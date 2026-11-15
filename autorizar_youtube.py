"""Se corre UNA sola vez: abre el navegador para que autorices al programa a subir videos a tu canal."""
from src.util import cargar_env, configurar_logs
from src.youtube import TOKEN, obtener_credenciales

if __name__ == "__main__":
    cargar_env()
    configurar_logs("autorizacion")
    obtener_credenciales(interactivo=True)
    print(f"\nListo. Permiso guardado en {TOKEN.name}. Ya podés correr: python producir.py")
