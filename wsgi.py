from app import app
import os
from dotenv import load_dotenv
import logging
        
load_dotenv()

# ロギングの設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# アプリケーションの作成
logger.info('アプリケーションを作成しました')

# Gunicorn用のアプリケーションエクスポート
application = app
logger.info('アプリケーションをエクスポートしました')

if __name__ == '__main__':
    # ローカル開発環境用
    port = int(os.environ.get('PORT', 5000))
    logger.info(f'アプリケーションを起動します。ポート: {port}')
    app.run(host='0.0.0.0', port=port)