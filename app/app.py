from flask import Flask, render_template, request, jsonify
import os

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'data/inputs'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file:
        filename = file.filename
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        return jsonify({'message': 'File uploaded successfully', 'filename': filename})

@app.route('/generate', methods=['POST'])
def generate_questions():
    # Placeholder for question generation logic
    # This will integrate with your RAG pipeline
    print("Generate Questions button clicked")
    return jsonify({'message': 'Question generation started', 'status': 'processing'})

if __name__ == '__main__':
    app.run(debug=True, port=5000)

