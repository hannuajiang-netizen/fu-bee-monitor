from flask import Flask, send_from_directory
from flask_cors import CORS
import os

from routes.task1 import task1_bp
from routes.task3 import task3_bp

app = Flask(__name__)
CORS(app)

# 注册路由
app.register_blueprint(task1_bp, url_prefix='/api/task1')
app.register_blueprint(task3_bp, url_prefix='/api/task3')

# 静态文件服务（生产环境）- 放在最后，避免拦截 API 路由
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    # 不处理 API 路径
    if path.startswith('api/'):
        return "Not Found", 404
    if path != "" and os.path.exists(os.path.join('../frontend/dist', path)):
        return send_from_directory('../frontend/dist', path)
    return send_from_directory('../frontend/dist', 'index.html')


if __name__ == '__main__':
    # 创建必要的目录
    os.makedirs('./uploads', exist_ok=True)
    os.makedirs('./data', exist_ok=True)
    
    print("=" * 50)
    print("fu之小蜜蜂监控后台 - 后端服务")
    print("=" * 50)
    print("API 地址: http://localhost:5000")
    print("=" * 50)
    
    app.run(host='0.0.0.0', port=5001, debug=True)