import chardet


def decode_file_content(content: bytes) -> str:
    """解码文件内容，自动检测编码"""
    if not content:
        raise ValueError("文件内容为空")

    # 检测编码
    detected = chardet.detect(content)
    encoding = detected.get('encoding')
    confidence = detected.get('confidence')

    # ✅ 关键修复：处理 confidence 为 None 的情况
    if confidence is None:
        confidence = 0.0

    print(f"📄 检测到编码: {encoding}, 置信度: {confidence:.2f}")

    # 如果编码检测失败或置信度低，尝试常见编码
    if encoding is None or confidence < 0.6:
        # 优先尝试中文编码
        for enc in ['gbk', 'gb2312', 'gb18030', 'utf-8']:
            try:
                text = content.decode(enc)
                print(f"✅ 使用备选编码 {enc} 解码成功")
                return text
            except UnicodeDecodeError:
                continue
        else:
            # 所有编码都失败，强制解码
            text = content.decode('utf-8', errors='ignore')
            print("⚠️ 使用 utf-8 强制解码（部分字符可能丢失）")
            return text

    # 使用检测到的编码解码
    try:
        return content.decode(encoding)
    except UnicodeDecodeError:
        # 如果解码失败，尝试备选
        for enc in ['gbk', 'gb2312', 'gb18030', 'utf-8']:
            try:
                return content.decode(enc)
            except UnicodeDecodeError:
                continue
        return content.decode('utf-8', errors='ignore')
