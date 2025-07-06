import base64
from typing import List, Union

from openai import OpenAI
from PIL import Image


class FormulaRecognizer:
    def __init__(self, api_key: str, model: str = "Qwen/Qwen2.5-72B-Instruct"):
        """
        初始化硅基流动API客户端
        :param api_key: 从硅基流动平台获取的API Key
        :param model: 模型名称，默认为Qwen2.5-72B-Instruct
        """
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.siliconflow.cn/v1"  # 硅基流动API端点
        )
        self.model = model

    def _encode_image(self, image_path: str) -> str:
        """将本地图像编码为base64格式"""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")

    def recognize(
        self, 
        image_paths: Union[str, List[str]], 
        prompt: str = None,
        max_tokens: int = 1024
    ) -> List[str]:
        """
        识别图像中的数学公式并返回LaTeX代码
        :param image_paths: 单张图像路径或图像路径列表
        :param prompt: 自定义提示词，默认为专业公式识别指令
        :param max_tokens: 最大输出token数
        :return: LaTeX公式列表（单行格式）
        """
        if isinstance(image_paths, str):
            image_paths = [image_paths]

        # 修改后的系统指令（禁止多行环境）
        system_prompt = """你是一个专业的数学公式识别系统，请严格按照以下要求操作：
1. 专注识别图像中的数学公式、符号、希腊字母、运算符等
2. 输出标准LaTeX代码，确保可被编译器解析
3. 所有公式必须转换为单行格式（禁止使用\\begin{{align}}等多行环境）
4. 多行公式用空格分隔或合并为单行
5. 不添加解释性文字，直接输出纯净的LaTeX代码"""

        user_prompt = prompt or "请将图中的数学公式转换为精确的单行LaTeX代码，禁止使用多行环境，不要添加任何额外描述。"

        results = []
        for img_path in image_paths:
            try:
                Image.open(img_path).verify()
            except Exception as e:
                raise ValueError(f"无效图像文件: {img_path}, 错误: {str(e)}")

            messages = [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user", 
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{self._encode_image(img_path)}"
                            }
                        },
                        {"type": "text", "text": user_prompt}
                    ]
                }
            ]

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=0.2
            )

            # 后处理：确保没有漏网的多行标记
            latex_code = response.choices[0].message.content
            latex_code = latex_code.replace("\\begin{align}", "").replace("\\end{align}", "")
            latex_code = latex_code.replace("\\begin{aligned}", "").replace("\\end{aligned}", "")
            latex_code = " ".join(latex_code.split())  # 合并多余空格
            
            results.append(latex_code)

        return results


# 使用示例
if __name__ == "__main__":
    API_KEY = "your_api_key_here"
    recognizer = FormulaRecognizer(api_key=API_KEY)
    
    # 示例识别
    latex_result = recognizer.recognize("formula.png")
    print("识别结果:", latex_result[0])