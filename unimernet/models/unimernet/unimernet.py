import torch
import torch.nn.functional as F
from unimernet.common.registry import registry
from unimernet.models.blip2_models.blip2 import Blip2Base
from unimernet.models.unimernet.encoder_decoder import DonutEncoderDecoder, DonutTokenizer


@registry.register_model("unimernet")
class UniMERModel(Blip2Base):
    """
    Nougat model for formula recognition.
    Supported model types:
        - default
    Usage:
        >>> from unimernet.models import load_model
        >>> model = load_model("unimernet", "default")
    """

    PRETRAINED_MODEL_CONFIG_DICT = {
        "default": "configs/models/unimernet_base.yaml",
        "unimernet": "configs/models/unimernet_base.yaml",
    }

    def __init__(
            self,
            *,
            model_name,
            model_config,
            tokenizer_name,
            tokenizer_config,
    ):
        super().__init__()

        self.tokenizer = DonutTokenizer(tokenizer_config.path)
        self.model = DonutEncoderDecoder(
            model_config.model_name,
            num_tokens=len(self.tokenizer),
            bos_token_id=self.tokenizer.bos_token_id,
            pad_token_id=self.tokenizer.pad_token_id,
            eos_token_id=self.tokenizer.eos_token_id,
        )
        self.max_seq_len = model_config.max_seq_len
        self.tokenizer.max_seq_len = self.max_seq_len

    def forward(self, samples):
        image, text = samples["image"], samples["text_input"]

        text_inputs = self.tokenizer.tokenize(text).to(image.device)
        count_gt = self._get_count_gt(text, image.device)
        tgt_seq, tgt_mask = text_inputs["input_ids"], text_inputs["attention_mask"]
        with self.maybe_autocast():
            loss = self.model(
                pixel_values=image,
                decoder_input_ids=tgt_seq,
                decoder_attention_mask=tgt_mask,
                decoder_count_gt=count_gt,
            )
        return {"loss": loss}

    def _get_count_gt(self, text, device):
        labels = self.tokenizer.tokenize(text, max_length=1536)["input_ids"].to(device)
        mask = labels != self.tokenizer.pad_token_id
        one_hot_labels = F.one_hot(labels, num_classes=self.tokenizer.tokenizer.vocab_size) * mask.unsqueeze(-1)
        count_gt = torch.sum(one_hot_labels, dim=1)
        return count_gt # (bs, vocab_size)

    @torch.no_grad()
    def generate(
            self,
            samples,
            temperature: float = 0.2,
            do_sample: bool = False,
            top_p: float = 0.95,
            **kwargs
    ):

        image = samples["image"]
        with self.maybe_autocast():
            outputs = self.model.generate(
                pixel_values=image,
                temperature=temperature,
                max_new_tokens=self.max_seq_len,
                decoder_start_token_id=self.tokenizer.tokenizer.bos_token_id,
                # decoder_end_token_id=self.tokenizer.tokenizer.eos_token_id,
                do_sample=do_sample,
                top_p=top_p,
                **kwargs
            )
        pred_tokens = self.tokenizer.detokenize(outputs)
        pred_str = self.tokenizer.token2str(outputs)
        return {"pred_tokens": pred_tokens, "pred_str": pred_str, "pred_ids": outputs}

    @classmethod
    def from_config(cls, cfg):

        model_name = cfg.get("model_name")
        model_config = cfg.get("model_config")
        tokenizer_name = cfg.get("tokenizer_name")
        tokenizer_config = cfg.get("tokenizer_config")

        model = cls(
            model_name=model_name,
            model_config=model_config,
            tokenizer_name=tokenizer_name,
            tokenizer_config=tokenizer_config
        )

        model.load_checkpoint_from_config(cfg)

        return model
