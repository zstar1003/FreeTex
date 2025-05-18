import torch
import os


def convert_to_fp16(state_dict: dict) -> dict:
    """将 state_dict 中所有 float32 张量转换为 float16"""
    return {
        k: v.half() if isinstance(v, torch.Tensor) and v.dtype == torch.float32 else v
        for k, v in state_dict.items()
    }


def convert_pth_to_fp16_keep_structure(input_path, output_path=None):
    print(f"加载模型文件: {input_path}")
    data = torch.load(input_path, map_location="cpu")

    if "model" in data:
        data["model"] = convert_to_fp16(data["model"])
    elif "state_dict" in data:
        data["state_dict"] = convert_to_fp16(data["state_dict"])
    else:
        data = convert_to_fp16(data)

    if output_path is None:
        base, _ = os.path.splitext(input_path)
        output_path = base + ".fp16.pth"

    torch.save(data, output_path)
    print(f"已保存 fp16 模型: {output_path}")


if __name__ == "__main__":
    convert_pth_to_fp16_keep_structure("models/unimernet_small/unimernet_small.pth")
