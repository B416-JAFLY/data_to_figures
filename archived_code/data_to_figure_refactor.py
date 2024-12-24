import base64
import anthropic
import matplotlib.pyplot as plt
import tempfile
import os
from datetime import datetime
import json

def encode_image_to_base64(image_path):
    """将图片转换为 Base64 格式，并返回图片的媒体类型"""
    with open(image_path, "rb") as f:
        image_data = base64.standard_b64encode(f.read()).decode("utf-8")
    
    ext = os.path.splitext(image_path)[-1].lower()
    if ext in [".jpeg", ".jpg"]:
        media_type = "image/jpeg"
    elif ext == ".png":
        media_type = "image/png"
    elif ext == ".gif":
        media_type = "image/gif"
    elif ext == ".webp":
        media_type = "image/webp"
    else:
        raise ValueError("Unsupported image type. Supported types are: JPEG, PNG, GIF, and WEBP.")
    
    return image_data, media_type

def call_claude_api(messages):
    """调用 Claude API 获取代码回复"""
    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=2048,
        messages=messages
    )   
    """调用 Claude API 获取代码回复"""
    
    if response:
        return response.content  
    else:
        print("API 调用失败")
        return None
    
def execute_code(code, output_path):
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

def handle_retry(messages, max_retries, output_path):
    """处理错误并重试调用 Claude API"""
    retries = 0
    while retries < max_retries:
        print("正在调用 Claude API...")
        response = call_claude_api(messages)
        
        if response:
            print("收到 Claude 的代码:\n", response)
            try:
                execute_code(response, output_path)
                print("图表生成成功！")
                return True, response[0].text
            except RuntimeError as e:
                print(f"执行代码失败: {e}")
                error_info = str(e)
                new_prompt = (
                    f"你的代码出现错误，\n"
                    f"代码执行出错的错误信息：{error_info}\n"
                    "请检查并修正上面的代码。"
                )
                messages = messages + [
                    {
                        "role": "assistant",
                        "content": [
                            {
                                "type": "text",
                                "text": response[0].text,
                            },
                        ],
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": new_prompt,
                            },
                        ],
                    },
                ]
                retries += 1
        else:
            print("未能从 Claude 获取代码，请检查输入或 API 状态。")
            retries += 1

    print("已达到最大重试次数，无法成功生成图表。")
    return False, None

def main():
    # 用户上传图片路径
    image_path = input("请输入图片路径: ")
    # 提取图片文件名（不含路径）并获取当前日期
    image_name = os.path.splitext(os.path.basename(image_path))[0]
    date_str = datetime.now().strftime("%Y%m%d_%H%M")
    
    output_path = f"{date_str}_{image_name}.png"

    # 读取图片并编码为 Base64
    image_data, media_type = encode_image_to_base64(image_path)
    
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
5.我的环境中没有GUI界面，不要出现plt.show()
  """
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
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

    is_success , code = handle_retry(messages, max_retries=3, output_path=output_path)

    if is_success:
        if "```python" in code and "```" in code:
            code = code.split("```python\n", 1)[-1].split("```", 1)[0]
        print("保存代码和文档")
        print("正在调用 Claude API...")
        prompt = f"""
请你帮我把下面的代码抽象为一个函数，函数名为generate_figure，函数的输入参数为图像所需要的路径，以及一些可以自定义的参数（如色彩、样式等），这些参数要有一个默认值。函数的输出为一个plt对象。下面是我需要你帮忙处理的代码：
{code}
"""        
        messages =[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt,
                    },
                ],
            },
        ]
        response = call_claude_api(messages)
        doc= response[0].text

        # 构造文件名
        json_filename = f"{date_str}_{image_name}.json"

        # 将 code 和 doc 保存到 JSON 文件
        with open(json_filename, 'w', encoding='utf-8') as json_file:
            json.dump({"code": code, "doc": doc}, json_file, ensure_ascii=False, indent=4)

        print(f"代码和文档已成功保存为 {json_filename}")
    
if __name__ == "__main__":
    main()