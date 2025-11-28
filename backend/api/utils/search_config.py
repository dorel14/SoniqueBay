import warnings
from whoosh.analysis import RegexTokenizer

def configure_whoosh_warnings():
    """Configure les avertissements de Whoosh et corrige les expressions régulières"""
    # Ignore les avertissements de syntaxe spécifiques à Whoosh
    warnings.filterwarnings("ignore", category=SyntaxWarning, module="whoosh")
    
    # Patch pour les regex problématiques
    def fix_regex(pattern):
        return pattern.replace(r'\S', r'[^\s]')
    
    # Création d'une nouvelle classe RegexTokenizer avec le pattern corrigé
    class SafeRegexTokenizer(RegexTokenizer):
        def __init__(self, expression=r"[^\s]+", gaps=False):
            fixed_expression = fix_regex(expression)
            super().__init__(expression=fixed_expression, gaps=gaps)
    
    # Remplace la classe originale par notre version sécurisée
    import whoosh.analysis
    whoosh.analysis.RegexTokenizer = SafeRegexTokenizer