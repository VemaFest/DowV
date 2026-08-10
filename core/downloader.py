import winreg
import logging
import yt_dlp

def obtener_navegador_por_defecto():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\Shell\Associations\UrlAssociations\http\UserChoice')
        prog_id, _ = winreg.QueryValueEx(key, 'ProgId')
        prog_id = prog_id.lower()
        
        if 'chrome' in prog_id:
            return 'chrome'
        elif 'edge' in prog_id:
            return 'edge'
        elif 'firefox' in prog_id:
            return 'firefox'
        elif 'brave' in prog_id:
            return 'brave'
        elif 'opera' in prog_id:
            return 'opera'
        elif 'vivaldi' in prog_id:
            return 'vivaldi'
        else:
            return None
    except Exception:
        return None

def extraer_info_robusto(ydl_opts_base, url, download=True):
    try:
        with yt_dlp.YoutubeDL(ydl_opts_base) as ydl:
            return ydl.extract_info(url, download=download)
    except Exception as e:
        error_msg = str(e).lower()
        necesita_cookies = any(kw in error_msg for kw in ['sign in', 'bot', '429', 'too many requests', 'cookie'])
        if necesita_cookies:
            logging.info("YouTube bloqueó la descarga. Intentando evasión con cookies locales...")
            navegadores = ['chrome', 'edge', 'firefox', 'brave', 'opera', 'vivaldi']
            def_nav = obtener_navegador_por_defecto()
            if def_nav and def_nav in navegadores:
                navegadores.remove(def_nav)
                navegadores.insert(0, def_nav)
                
            for nav in navegadores:
                logging.info(f"Probando extraer cookies de: {nav}")
                opts = dict(ydl_opts_base)
                opts['cookiesfrombrowser'] = (nav,)
                try:
                    with yt_dlp.YoutubeDL(opts) as ydl2:
                        return ydl2.extract_info(url, download=download)
                except Exception as ex:
                    logging.warning(f"Fallo al usar cookies de {nav}")
                    continue
        raise e
