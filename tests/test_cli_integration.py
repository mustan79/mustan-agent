"""Run the actual SDK and CLI against a local model protocol fixture."""
import json
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer


def test_operate_with_local_openai_compatible_server(tmp_path):
    replies = iter([
        '["Create hello.py", "Read hello.py", "Finish"]',
        '<thought>Create file</thought>\n```write_file\n{"file_path":"hello.py","content":"print(42)\\n"}\n```',
        '<thought>Verify file</thought>\n```read_file\n{"file_path":"hello.py"}\n```',
        '<thought>Finished</thought><final>Created and read hello.py.</final>',
    ])
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            requests.append(json.loads(self.rfile.read(int(self.headers['Content-Length']))))
            response = {
                'id': 'test-completion', 'object': 'chat.completion',
                'created': 0, 'model': 'fixture-model',
                'choices': [{'index': 0, 'message': {'role': 'assistant', 'content': next(replies)}, 'finish_reason': 'stop'}],
                'usage': {'prompt_tokens': 10, 'completion_tokens': 10, 'total_tokens': 20},
            }
            body = json.dumps(response).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = HTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    (tmp_path / 'mustan_settings.json').write_text(json.dumps({'llm': {
        'provider': 'ollama', 'model': 'fixture-model',
        'ollama_base_url': f'http://127.0.0.1:{server.server_port}/v1',
    }}), encoding='utf-8')
    try:
        result = subprocess.run(
            [sys.executable, '-m', 'main', 'operate', 'Create hello.py and read it'],
            cwd=tmp_path, capture_output=True, encoding='utf-8', timeout=30,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        assert (tmp_path / 'hello.py').read_text(encoding='utf-8') == 'print(42)\n'
        assert len(requests) == 4
        assert all(request['model'] == 'fixture-model' for request in requests)
        events = list((tmp_path / 'Aimemory' / 'telemetry').glob('*.jsonl'))
        assert events
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
