import base64
import anthropic
import matplotlib.pyplot as plt
import tempfile
import os

# 模拟调用 Claude 的函数
def send_to_claude(image_path, prompt, conversation_history=[]):
    # 将图片读取并转成 base64 格式
    with open(image_path, "rb") as f:
        image_data = base64.standard_b64encode(f.read()).decode("utf-8")
    
    # 根据图片路径判断图片类型
    ext = os.path.splitext(image_path)[-1].lower()
    if ext == ".jpeg" or ext == ".jpg":
        image_media_type = "image/jpeg"
    elif ext == ".png":
        image_media_type = "image/png"
    elif ext == ".gif":
        image_media_type = "image/gif"
    elif ext == ".webp":
        image_media_type = "image/webp"
    else:
        raise ValueError("Unsupported image type. Supported types are: JPEG, PNG, GIF, and WEBP.")
    
    # 构造 API 请求数据
    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=1024,
        messages=conversation_history + [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": image_media_type,
                            "data": image_data,
                        },
                    },
                    {
                        "type": "text",
                        "text": prompt,
                    },
                ],
            }
        ]
    )
    
    # 检查响应并返回结果
    if response:
        return response.content  # 假设 Claude 返回的代码在 content 字段
    else:
        print("API 调用失败")
        return None

def execute_and_save_code(code, output_path):
    try:
        # 确保 code 是字符串
        if isinstance(code, list) and len(code) > 0 and hasattr(code[0], 'text'):
            code = code[0].text  # 提取文本内容

        # 从代码块中提取实际代码
        if "```python" in code and "```" in code:
            code = code.split("```python\n", 1)[-1].split("```", 1)[0]

        if not isinstance(code, str):
            raise ValueError("返回的代码内容格式不正确，无法执行。")

        # 执行代码
        exec(code, {"plt": plt})

        # 刷新绘图上下文并保存
        plt.gcf().canvas.draw_idle()  # 强制刷新绘图上下文
        plt.savefig(output_path)

        # 清除当前图表
        plt.close()
        print(f"图片已保存到: {output_path}")
    
    except Exception as e:
        raise RuntimeError(f"代码执行出错: {e}")

# 主函数
def main():
    # 用户上传图片路径
    image_path = input("请输入图片路径: ")
    
    # 提示词
    prompt = """
观察上面的图像，图像中是一个什么样的曲线？曲线中有哪些要素？
1.请你帮我使用Python代码复现这张figures
2.复现的时候，尤其注意原图的色彩风格，图形样式，力求与原图一致
3.如果你读取图中数据有困难，可以自己生成示例数据
注意，我会将你回答的内容直接放进一个exec(code, {"plt": plt})语句中，所以:
1.请你保证你返回的内容直接就是一个可以执行的代码，不要包括解释或者markdown元素等内容
2.你绘制的图像应该保存在一个plt对象中，以便我提取回传到其他逻辑里
3.在添加颜色条时，确保绑定到正确的图形对象 (使用 fig.colorbar)。
4.避免出现紧凑布局与颜色条冲突的问题。
  """
    
    # 初始化对话历史和重试次数
    conversation_history = []
    max_retries = 3
    retries = 0

    while retries < max_retries:
        print("正在调用 Claude API...")
        response = send_to_claude(image_path, prompt, conversation_history)
        
        if response:
            print("收到 Claude 的代码:\n", response)
            
            # 创建临时文件保存图片
            output_path = os.path.join(tempfile.gettempdir(), "recreated_image.png")
            
            try:
                # 尝试执行代码并保存图片
                execute_and_save_code(response, output_path)
                print("图表生成成功！")
                return
            except RuntimeError as e:
                print(f"执行代码失败: {e}")
                # 构建新的 prompt 和对话历史
                error_info = str(e)
                new_prompt = (
                    f"请根据这张图片生成一个可以复现此图的Python代码。\n"
                    f"原始 prompt: {prompt}\n"
                    f"模型的代码回复：{response}\n"
                    f"代码执行出错的错误信息：{error_info}\n"
                    "请检查并修正上面的代码。"
                )
                conversation_history.append({"role": "user", "content": prompt})
                conversation_history.append({"role": "assistant", "content": response})
                prompt = new_prompt
                retries += 1
        else:
            print("未能从 Claude 获取代码，请检查输入或 API 状态。")
            retries += 1

    print("已达到最大重试次数，无法成功生成图表。")

if __name__ == "__main__":
    main()
