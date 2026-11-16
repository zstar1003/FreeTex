# 公式识别 Badcase 的离线回归与定位

## #37 调查范围

参考 [Badcase 征集 #37](https://github.com/zstar1003/FreeTex/issues/37)。以下结论基于源码 `89f30a63cc9a2507b3da9c9aa0ca5a9f90757bd0`，不是模型准确率评测，也不表示该 issue 已解决。

- [维护者示例](https://github.com/zstar1003/FreeTex/issues/37#issuecomment-3208873898) 涉及矩阵、前置上下标和分式。截图可见输出与输入存在差异，但没有原始返回 LaTeX、完整配置或模型版本，不能据此确定问题发生在识别、后处理还是渲染。
- [贡献者示例](https://github.com/zstar1003/FreeTex/issues/37#issuecomment-4160107133) 明确使用硅基流动的 `Qwen/Qwen2.5-VL-72B-Instruct`，包含嵌套分式与求和。该名称是服务上的模型标识，不等同于固定权重修订。截图没有原始返回 LaTeX、应用版本或服务端模型修订，不能仅凭排版尺寸判定公式内容丢失。
- 默认本地配置是 `unimernet_small`，不能用它的结果替代上述云模型的复现。仓库不包含本地模型权重。本次没有执行真实模型推理、调用云 API 或上传截图。

## 先分清三个阶段

1. **识别请求**：`tools/local_processor.py::_process_with_multimodal` 将 PIL 图像编码为 PNG，通过配置的地址、模型和系统提示词调用 `chat.completions.create`。当前参数为 `max_tokens=1024`、`temperature=0.2`。模型列表测试不能验证视觉识别能力。
2. **字符串后处理**：移除 `align` / `aligned` 环境的起止标记，合并空白。它不通用删除求和上下限、索引或分式花括号，也不补全模型未返回的内容。此描述不保证所有 LaTeX 环境都可正确转换。
3. **渲染**：`main.py::render_latex_to_html` 使用资源模板；`resources/mathview/index.html` 用 KaTeX 的显示数学分隔符渲染。嵌套分式的字号、求和符号大小与限标位置不能单独作为内容错误的证据。

## 不联网的管线回归

在仓库根目录运行：

```sh
python -m unittest discover -s tests -p 'test_multimodal_formula_preservation.py' -v
```

测试从生产源码提取真实后处理方法，完全 mock OpenAI SDK 和图片输入，不需要密钥或模型权重。合成公式检查嵌套分式、求和上下限和索引保留；另检查选定模型、提示词、图像数据与请求端点。合成公式不是贡献者样例的标准答案。测试通过只说明这些管线行为未回归，**不证明识别准确率提高，也不测试 KaTeX 渲染或完整 GUI**。

## 为后续样例保留最小可复现材料

在获得图片使用许可后，优先本地保存，不默认上传到第三方模型或提交到公开仓库：

- 应用提交 SHA、平台，以及原图裁剪/缩放步骤；
- 本地模型权重版本，或云端供应商、模型标识、可获得的模型修订与测试时间；
- 系统提示词和生成参数，不包含 API key、Authorization 头、用户路径或其他敏感信息；
- 模型原始返回 LaTeX、后处理后的 LaTeX、渲染截图，分别记录；
- 人工核对的期望 LaTeX，并说明错字、结构错误还是仅排版差异；
- 如返回被截断，记录脱敏后的完成原因，不把截断当作准确率结论。

定位方法：原始返回已错则调查模型/提示词/输入；原始正确而后处理错误则为后处理增加最小合成回归；字符串正确但显示错误则用同一字符串独立复现 KaTeX。不要从一张结果截图自动修改数学内容或宣称 Badcase 已修复。
