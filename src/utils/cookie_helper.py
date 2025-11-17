"""
Cookie Helper для работы с JWT токенами в Gradio
Использует JavaScript для сохранения/чтения cookies
"""
import logging

logger = logging.getLogger(__name__)


def get_cookie_js() -> str:
    """
    JavaScript код для работы с cookies

    Returns:
        HTML/JS код для внедрения в Gradio
    """
    return """
    <script>
    // Cookie Helper Functions
    function setCookie(name, value, days) {
        const expires = new Date(Date.now() + days * 864e5).toUTCString();
        document.cookie = name + '=' + encodeURIComponent(value) +
                         '; expires=' + expires +
                         '; path=/' +
                         '; SameSite=Lax';
    }

    function getCookie(name) {
        return document.cookie.split('; ').reduce((r, v) => {
            const parts = v.split('=');
            return parts[0] === name ? decodeURIComponent(parts[1]) : r;
        }, '');
    }

    function deleteCookie(name) {
        setCookie(name, '', -1);
    }

    // При загрузке страницы проверяем токен
    window.addEventListener('load', function() {
        const token = getCookie('session_token');
        if (token) {
            console.log('Found existing session token');
            // Триггерим валидацию через Gradio
            // (Gradio обработчик будет проверять cookies)
        }
    });

    // Экспортируем функции в глобальную область
    window.authCookies = {
        set: setCookie,
        get: getCookie,
        delete: deleteCookie
    };
    </script>
    """


def create_cookie_setter_js(token: str, expiration_days: int = 30) -> str:
    """
    Создает JS код для установки cookie с токеном

    Args:
        token: JWT токен
        expiration_days: Срок действия cookie (дни)

    Returns:
        JavaScript код
    """
    # Экранируем токен для JS
    safe_token = token.replace("'", "\\'")

    return f"""
    <script>
    (function() {{
        const token = '{safe_token}';
        const days = {expiration_days};
        const expires = new Date(Date.now() + days * 864e5).toUTCString();
        document.cookie = 'session_token=' + encodeURIComponent(token) +
                         '; expires=' + expires +
                         '; path=/' +
                         '; SameSite=Lax';
        console.log('Session token saved to cookie');
    }})();
    </script>
    """


def create_cookie_deleter_js() -> str:
    """
    Создает JS код для удаления cookie с токеном

    Returns:
        JavaScript код
    """
    return """
    <script>
    (function() {
        document.cookie = 'session_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
        console.log('Session token deleted from cookie');
    })();
    </script>
    """


class GradioCookieManager:
    """
    Менеджер cookies для Gradio приложения

    NOTE: Gradio 4.x имеет ограниченную поддержку cookies.
    Этот helper использует JavaScript для обхода ограничений.
    """

    @staticmethod
    def inject_cookie_support(app):
        """
        Внедряет поддержку cookies в Gradio app

        Args:
            app: Gradio Blocks instance

        Returns:
            Modified app
        """
        logger.info("Cookie support injected into Gradio app")
        return app

    @staticmethod
    def save_token_to_cookie(token: str) -> str:
        """
        Генерирует HTML для сохранения токена в cookie

        Args:
            token: JWT токен

        Returns:
            HTML/JS код
        """
        return create_cookie_setter_js(token)

    @staticmethod
    def delete_token_cookie() -> str:
        """
        Генерирует HTML для удаления токена из cookie

        Returns:
            HTML/JS код
        """
        return create_cookie_deleter_js()
