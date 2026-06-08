"""NSFW Prompt Engineer - Bypass filters with AI-powered rewrites"""
import json

def run(request):
    """
    Take an NSFW request and return optimal prompts for different generators.
    Args: request (str) - what user wants
    Returns: dict of prompts for different services
    """
    bypass_dict = {
        "sex": "intimate passionate embrace",
        "naked": "without clothing figure study",
        "nude": "unclothed artistic figure study",
        "dick": "phallus marble sculpture",
        "cock": "erect male figure statue",
        "pussy": "female form intimate detail",
        "tits": "bust figure sculpture study",
        "ass": "posterior curve study",
        "fucking": "intimate connection passionate",
        "blowjob": "intimate oral caress artistic",
        "cum": "artistic fluid dynamics study",
        "orgasm": "ecstatic expression of pleasure",
    }
    
    # Generate variants for different services
    return {
        "pollinations": _rewrite_for_pollinations(request, bypass_dict),
        "artistic": f"artistic {request} oil painting classical",
        "photorealistic": f"photorealistic {request} studio lighting 8k",
        "anime": f"anime style {request} high quality illustration",
    }

def _rewrite_for_pollinations(text, bypass):
    text = text.lower()
    for original, replacement in bypass.items():
        text = text.replace(original, replacement)
    # Add artistic context
    text += ", professional photography, studio lighting, high quality, detailed"
    return text[:500]
