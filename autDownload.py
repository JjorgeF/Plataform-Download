import logging
import subprocess
import re
import os
import shutil # Importação da biblioteca shutil para verificar o caminho do executável | Não é tão necessário, mas é bom para encontrar/evitar possíveis erros/bugs
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --- CONFIGURAÇÃO ---
TELEGRAM_TOKEN = "8433505098:AAEidAVqKqIEiWIC9PhzjWgKfA_sxBX40ug" # Token da API do telegram/Whatsapp/Etc
# Use um caminho absoluto C:\\Users\\SeuUsuario\\Downloads --> as pastas do ubuntu as vezes atrapalham devido a diferenças de permissões
PASTA_DOWNLOADS = "/Documentos/arquivos/aut/downloadPasta"
# Expressão pra tentar ler links tanto do yt convecional, quanto do yt shorts
YOUTUBE_REGEX = r'(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)([a-zA-Z0-9_-]{11})'
# Expressão do yt-dlp para pegar o nome do arquivo quando o yt-dlp baixa ele
FILENAME_REGEX = r'\[download\] Destination: (.+)'

# logging para visualizar o terminal
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- FUNÇÕES DO BOT TROUXA ---

# função para quando os usuários enviam o /start no chat e o bot retorna isso
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    await update.message.reply_html(
        f"Fala Jubileu, vulgo {user.mention_html()}!\n\n"
        f"Manda o link do YouTube ai pai, vou baixar e te mandar de volta."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Responde a qualquer mensagem que não seja um comando, baixando e enviando o áudio."""
    text = update.message.text
    match = re.search(YOUTUBE_REGEX, text)

    if match:
        video_url = match.group(0) # pega o link do yt ou yt shorts
        logger.info(f"Link válido: {video_url}")
        
        await update.message.reply_text("Link válido! Deixa eu baixar aqui...")

        # Verifica se o yt-dlp está no PATH -- tava tentando encontrar o pq de alguns erros -- no fim era permissão do bot ao acesso das pastas do ubuntu
        # Solucionei dando um chmod u + w nas pastas que o bot precisa "enxergar", tanto para baixar o vídeo/áudio quanto na pasta que ele salva o arquivo e reenviar para o usuário
        ytdlp_path = shutil.which("yt-dlp")
        if not ytdlp_path:
            error_message = (
                "❌ Erro: O programa 'yt-dlp' não foi encontrado. "
                "Por favor, instale-o usando 'pip install yt-dlp' ou "
                "adicione o diretório do executável à sua variável de ambiente PATH."
            )
            logger.error(error_message)
            await update.message.reply_text(error_message)
            return # Sai da função se o yt-dlp não for encontrado

        file_path = None
        try:
            # Comando que será executado no terminal
            # Usando o caminho absoluto encontrado
            command = [
                ytdlp_path,
                "-o", "%(title)s.%(ext)s",
                "--format", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]",
                "-P", PASTA_DOWNLOADS,
                video_url
            ]

            result = subprocess.run(command, check=True, capture_output=True, text=True)
            
            logger.info(f"Saída do yt-dlp: {result.stdout}")
            
            filename_match = re.search(FILENAME_REGEX, result.stdout)
            if not filename_match:
                raise Exception("Não foi possível encontrar o nome do arquivo na saída do yt-dlp.")
            
            file_path = filename_match.group(1).strip()
            
            await update.message.reply_text("Download concluído! Fazendo o upload do vídeo...")
            
            with open(file_path, 'rb') as video_file:
                await update.message.reply_video(
                    video=video_file,
                    caption="Aqui está o seu vídeo! ✅"
                )
            
            await update.message.reply_text("Vídeo enviado com sucesso!")

        except subprocess.CalledProcessError as e:
            logger.error(f"Erro ao baixar o vídeo: {e.stderr}")
            await update.message.reply_text(f"❌ Ocorreu um erro ao tentar baixar o vídeo.\n\nDetalhes: {e.stderr}")
        except Exception as e:
            logger.error(f"Um erro inesperado ocorreu: {e}")
            await update.message.reply_text(f"❌ Um erro inesperado ocorreu: {e}")
        finally:
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    logger.info(f"Arquivo {file_path} deletado com sucesso.")
                except OSError as e:
                    logger.error(f"Erro ao deletar o arquivo: {e}")
    else:
        await update.message.reply_text("Isso não é um link válido do YouTube. Por favor, envie um link.")

def main() -> None:
    """Inicia o bot."""
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("Bot iniciado. Pressione Ctrl+C para parar.")
    application.run_polling()

if __name__ == "__main__":
    os.makedirs(PASTA_DOWNLOADS, exist_ok=True)
    main()
