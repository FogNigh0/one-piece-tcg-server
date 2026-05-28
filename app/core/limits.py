# app/core/limits.py
# Límites del sistema Freemium. Centralizado para que backend y admin los usen.

FREE_MAX_FOLDERS = 3          # carpetas de usuario (sin contar "Colección")
FREE_MAX_CARDS_PER_FOLDER = 100
DECK_MAX_CARDS = 51           # límite universal de cartas en un mazo (incluye líder)


def max_folders(is_premium: bool) -> int:
    """Devuelve -1 para ilimitado (premium) o el límite free."""
    return -1 if is_premium else FREE_MAX_FOLDERS


def max_cards_for_folder(is_premium: bool, folder_type: str) -> int:
    """
    Devuelve el límite de cartas para una carpeta según tipo y plan.
    - deck → siempre 51 (incluye premium)
    - collection / trade → ilimitado si premium, 100 si free
    - 'colección' principal (description == '__collection__') → free: 100, premium: -1
    """
    if folder_type == "deck":
        return DECK_MAX_CARDS
    return -1 if is_premium else FREE_MAX_CARDS_PER_FOLDER
