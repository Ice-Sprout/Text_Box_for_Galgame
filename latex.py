import re
from typing import Optional, Union

# ===== 依赖导入与后备实现 =====
try:
    from unicodeit import replace as unicodeit_replace
    UNICODEIT_AVAILABLE = True
except ImportError:
    UNICODEIT_AVAILABLE = False
    print("警告: 未找到 unicodeit 库，LaTeX 转换功能将受限")
    print("请安装: pip install unicodeit")

    # 基础LaTeX符号映射（后备实现）
    BASIC_LATEX_REPLACEMENTS = {
        r'\alpha': 'α', r'\beta': 'β', r'\gamma': 'γ', r'\delta': 'δ',
        r'\epsilon': 'ε', r'\zeta': 'ζ', r'\eta': 'η', r'\theta': 'θ',
        r'\iota': 'ι', r'\kappa': 'κ', r'\lambda': 'λ', r'\mu': 'μ',
        r'\nu': 'ν', r'\xi': 'ξ', r'\pi': 'π', r'\rho': 'ρ',
        r'\sigma': 'σ', r'\tau': 'τ', r'\upsilon': 'υ', r'\phi': 'φ',
        r'\chi': 'χ', r'\psi': 'ψ', r'\omega': 'ω',
        r'\Gamma': 'Γ', r'\Delta': 'Δ', r'\Theta': 'Θ', r'\Lambda': 'Λ',
        r'\Xi': 'Ξ', r'\Pi': 'Π', r'\Sigma': 'Σ', r'\Upsilon': 'Υ',
        r'\Phi': 'Φ', r'\Psi': 'Ψ', r'\Omega': 'Ω',
        r'\times': '×', r'\div': '÷', r'\pm': '±', r'\mp': '∓',
        r'\cdot': '·', r'\leq': '≤', r'\geq': '≥', r'\neq': '≠',
        r'\approx': '≈', r'\equiv': '≡', r'\in': '∈', r'\notin': '∉',
        r'\subset': '⊂', r'\supset': '⊃', r'\subseteq': '⊆', r'\supseteq': '⊇',
        r'\cup': '∪', r'\cap': '∩', r'\emptyset': '∅', r'\infty': '∞',
        r'\nabla': '∇', r'\partial': '∂', r'\forall': '∀', r'\exists': '∃',
        r'\therefore': '∴', r'\because': '∵', r'\angle': '∠', r'\parallel': '∥',
        r'\perp': '⊥', r'\int': '∫', r'\sum': '∑', r'\prod': '∏',
        r'\lim': 'lim', r'\log': 'log', r'\ln': 'ln', r'\sin': 'sin',
        r'\cos': 'cos', r'\tan': 'tan', r'\cot': 'cot', r'\sec': 'sec',
        r'\csc': 'csc',
        r'\leftarrow': '←', r'\rightarrow': '→', r'\leftrightarrow': '↔',
        r'\uparrow': '↑', r'\downarrow': '↓', r'\updownarrow': '↕',
        r'\Leftarrow': '⇐', r'\Rightarrow': '⇒', r'\Leftrightarrow': '⇔',
        r'\ldots': '…', r'\cdots': '⋯', r'\vdots': '⋮', r'\ddots': '⋱',
    }

    def unicodeit_replace(latex_text: str) -> str:
        """简单的 LaTeX 到 Unicode 转换后备实现"""
        if not isinstance(latex_text, str) or latex_text.strip() == "":
            return latex_text

        # 替换基础LaTeX符号
        result = latex_text
        for latex, unicode_char in BASIC_LATEX_REPLACEMENTS.items():
            result = result.replace(latex, unicode_char)

        # 安全的上下标转换（仅处理字母/数字）
        def safe_superscript(match: re.Match) -> str:
            """安全转换上标"""
            content = match.group(1) if match.group(1) else match.group(2)
            superscript_chars = []
            for c in content:
                if c.isdigit():
                    # 数字上标：0-9 → ⁰-⁹
                    superscript_chars.append(chr(ord(c) + 0x2070))
                elif c.islower():
                    # 小写字母上标：a-z → ᵃ-ᶻ（部分字符无标准上标，直接保留）
                    offset = ord(c) - ord('a')
                    superscript_ord = [0x1D43, 0x1D47, 0x1D9C, 0x1D48, 0x1D49,
                                       0x1D4B, 0x1D4D, 0x1D4F, 0x1D50, 0x1D52,
                                       0x1D56, 0x1D57, 0x1D58, 0x1D59, 0x1D5A,
                                       0x1D5B, 0x1D5C, 0x1D5D, 0x1D5E, 0x1D5F,
                                       0x1D60, 0x1D61, 0x1D62, 0x1D63, 0x1D64, 0x1D65].get(offset, ord(c))
                    superscript_chars.append(chr(superscript_ord) if superscript_ord != ord(c) else c)
                else:
                    # 非字母/数字直接保留
                    superscript_chars.append(c)
            return ''.join(superscript_chars)

        def safe_subscript(match: re.Match) -> str:
            """安全转换下标"""
            content = match.group(1) if match.group(1) else match.group(2)
            subscript_chars = []
            for c in content:
                if c.isdigit():
                    # 数字下标：0-9 → ₀-₉
                    subscript_chars.append(chr(ord(c) + 0x2080))
                elif c.islower():
                    # 小写字母下标：a-z → ₐ-ⱼ（部分字符无标准下标，直接保留）
                    offset = ord(c) - ord('a')
                    subscript_ord = [0x2090, 0x2091, 0x2092, 0x2093, 0x2094,
                                     0x2095, 0x2096, 0x2097, 0x2098, 0x2099,
                                     0x209A, 0x209B, 0x209C, 0x209D, 0x209E,
                                     0x209F, 0x1D62, 0x1D63, 0x1D64, 0x1D65,
                                     0x1D66, 0x1D67, 0x1D68, 0x1D69, 0x1D6A, 0x1D6B].get(offset, ord(c))
                    subscript_chars.append(chr(subscript_ord) if subscript_ord != ord(c) else c)
                else:
                    # 非字母/数字直接保留
                    subscript_chars.append(c)
            return ''.join(subscript_chars)

        # 匹配带大括号的上下标：^{...} / _{...}
        result = re.sub(r'\^\{([^}]+)\}', safe_superscript, result)
        result = re.sub(r'_\{([^}]+)\}', safe_subscript, result)
        # 匹配单个字符的上下标：^x / _x
        result = re.sub(r'\^([a-zA-Z0-9])', safe_superscript, result)
        result = re.sub(r'_([a-zA-Z0-9])', safe_subscript, result)

        return result

# ===== LaTeX转换类 =====
class LatexConverter:
    def __init__(self):
        self.latex_pattern = re.compile(
            r'(\\[a-zA-Z]+)|(\^+\{?[a-zA-Z0-9]+\}?)|(_+\{?[a-zA-Z0-9]+\}?)|(\\frac|\\sqrt|\\sum|\\int|\\prod)',
            re.IGNORECASE
        )

    def convert_latex_to_unicode(self, latex_text: Optional[Union[str, None]]) -> str:
        """
        安全转换LaTeX公式到Unicode
        :param latex_text: 待转换的文本，允许为None/空字符串
        :return: 转换后的文本
        """
        # 严格判空，处理非字符串类型
        if not isinstance(latex_text, str) or latex_text.strip() == "":
            return "" if latex_text is None else latex_text

        try:
            return unicodeit_replace(latex_text)
        except Exception as e:
            print(f"LaTeX 转换错误: {e}")
            return latex_text

    def is_latex_formula(self, text: Optional[Union[str, None]]) -> bool:
        """
        严格判断文本是否包含LaTeX公式（避免误判普通符号）
        :param text: 待检测文本，允许为None/空字符串
        :return: 是否为LaTeX公式
        """
        if not isinstance(text, str) or text.strip() == "":
            return False

        # 仅当匹配到LaTeX命令/数学结构时，才判定为LaTeX公式
        return bool(self.latex_pattern.search(text))

# ===== 全局实例与核心函数 =====
# 延迟初始化，避免导入时报错
latex_converter = LatexConverter()

def convert_latex_in_text(text: Optional[Union[str, None]]) -> str:
    """
    转换文本中的LaTeX公式（安全封装）
    :param text: 待转换文本，允许为None/空字符串
    :return: 转换后的文本
    """
    # 空文本直接返回，避免触发转换逻辑
    if not isinstance(text, str) or text.strip() == "":
        return "" if text is None else text

    # 仅当判定为LaTeX公式时，才进行转换
    if latex_converter.is_latex_formula(text):
        return latex_converter.convert_latex_to_unicode(text)

    return text