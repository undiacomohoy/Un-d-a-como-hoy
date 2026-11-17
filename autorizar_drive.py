"""Autoriza (una sola vez) que el sistema deje los informes semanales en tu Google Drive.
Iniciá sesión con la cuenta de Google donde está tu Drive (la de los agentes de la oficina)."""
from src import drive

if __name__ == "__main__":
    drive.obtener_credenciales(interactivo=True)
    drive.subir_texto("Informe de prueba.md", "# Conexión lista\n\nEl sistema ya puede dejar informes en esta carpeta.\n")
    print("\nListo: se creó la carpeta 'Informes de canales' en tu Drive con un archivo de prueba.")
