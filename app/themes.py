"""Named colour and layout themes for the app and the deck.

Every colour in ``static/styles.css`` (app) and ``static/story.css`` (deck) is a CSS custom
property. A theme overrides them, so a new look is a new entry here, not a CSS edit.
Pick one per demo (``Demo.theme``), for the whole app (``DEMO_THEME``), or live in the
room with ``?theme=<name>`` on any page.
"""
from markupsafe import Markup, escape

THEMES = {
    # The original look: light, neutral app; dark, high-contrast deck.
    "lakehouse-night": {
        "label": "Lakehouse Night",
        "fonts_url": "https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500;12..96,700;12..96,800&family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600&display=swap",
        "app": {},  # the defaults in styles.css
        "deck": {},  # the defaults in story.css
        "theme_color": {"app": "#f7f8fa", "deck": "#0a1014"},
    },
    # Light, fresh and a bit playful: cream paper, leaf green, tomato and mango.
    "fresh-market": {
        "label": "Fresh Market",
        "fonts_url": "https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500;12..96,700;12..96,800&family=DM+Mono:wght@400;500&family=DM+Sans:opsz,wght@9..40,400;9..40,500;9..40,600;9..40,700&display=swap",
        "app": {
            "canvas": "#f6f4ec", "surface": "#fffdf8", "subtle": "#efebe0", "ink": "#17301f",
            "ink-soft": "#34503e", "muted": "#66786b", "faint": "#93a296", "line": "#e5e0d2",
            "accent": "#ff5c39", "accent-soft": "#ffece5", "accent-ink": "#c23a1c",
            "on-accent": "#ffffff", "green": "#2f9e5b", "green-soft": "#e8f5ec",
            "amber": "#b86e00", "amber-soft": "#fff2d6", "series-1": "#17301f",
            "series-2": "#f2a93b", "series-3": "#2f9e5b", "series-bar": "#d9d3c3",
            "highlight": "#fff1cc", "radius": "14px",
            "font-body": '"DM Sans", system-ui, sans-serif',
            "font-head": '"Bricolage Grotesque", "DM Sans", sans-serif',
        },
        "deck": {
            "stage-bg": "#e7ede1", "slide-bg": "#fbf8f1", "panel": "#ffffff", "panel-2": "#f3efe5",
            "line": "#e3ddcf", "text": "#17301f", "text-soft": "#3d5546", "muted": "#6b7f70",
            "faint": "#9aa89c", "coral": "#ff5c39", "coral-soft": "#c23a1c", "on-coral": "#ffffff",
            "mint": "#2f9e5b", "amber": "#b86e00", "slate": "#7b8f86",
            "glow-a": "rgba(255, 92, 57, .10)", "glow-b": "rgba(47, 158, 91, .12)",
            "dots": "rgba(23, 48, 31, .07)", "radius": "22px",
            "font-body": '"DM Sans", system-ui, sans-serif',
            "font-mono": '"DM Mono", ui-monospace, monospace',
        },
        "theme_color": {"app": "#f6f4ec", "deck": "#fbf8f1"},
    },
}
DEFAULT_THEME = "lakehouse-night"


def resolve(name: str | None) -> str:
    return name if name in THEMES else DEFAULT_THEME


def head_tags(name: str, surface: str) -> Markup:
    """Font link, theme-color and the :root overrides for ``surface`` ('app' or 'deck')."""
    theme = THEMES[resolve(name)]
    # Theme values are trusted config; "<" is dropped so a value can never close the tag.
    tokens = "".join(f"--{key}: {value};" for key, value in theme[surface].items()).replace("<", "")
    return Markup(
        f'<meta name="theme-color" content="{escape(theme["theme_color"][surface])}">'
        f'<link rel="preconnect" href="https://fonts.googleapis.com">'
        f'<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
        f'<link rel="stylesheet" href="{escape(theme["fonts_url"])}">'
        f"<style>:root {{{tokens}}}</style>"
    )
