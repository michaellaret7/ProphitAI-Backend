# src/phaseOne/__init__.py
# Expose key functions/classes from phaseOne modules

from .phaseOneAnimation import Colors, AnimationController, start_animation
from .phaseOneFormatting import format
from .phaseOneRun import optimize, validate_and_fix_allocations, validate_asset_classes, parse_json_with_openai

__all__ = [
    # phaseOneAnimation exports
    'Colors', 'AnimationController', 'start_animation',
    
    # phaseOneFormatting exports
    'format',
    
    # phaseOneRun exports
    'optimize', 'validate_and_fix_allocations', 'validate_asset_classes', 'parse_json_with_openai'
] 