import os
import json
import time
import re
from flask import Flask, request, jsonify, send_file, render_template_string, Response
import yt_dlp

app = Flask(__name__)

# --- CONFIGURATION ---
# Use a temporary directory for downloads
DOWNLOAD_FOLDER = '/tmp' if os.path.exists('/tmp') else 'downloads'
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

# --- FRONTEND TEMPLATE (HTML/CSS/JS) ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NexStream | YT Downloader</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        body {
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            min-height: 100vh;
            color: #e2e8f0;
            font-family: 'Inter', sans-serif;
        }
        .glass-panel {
            background: rgba(30, 41, 59, 0.7);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        .loader {
            border-top-color: #3b82f6;
            -webkit-animation: spinner 1.5s linear infinite;
            animation: spinner 1.5s linear infinite;
        }
        @keyframes spinner {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    </style>
</head>
<body class="flex items-center justify-center p-4">

    <div class="w-full max-w-3xl glass-panel rounded-2xl shadow-2xl overflow-hidden p-6 md:p-8">
        <div class="text-center mb-8">
            <h1 class="text-3xl md:text-4xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-purple-500 mb-2">
                NexStream
            </h1>
            <p class="text-slate-400 text-sm">Download Videos, Audio & Transcripts Instantly</p>
        </div>

        <div class="relative mb-8">
            <div class="flex items-center bg-slate-800/50 rounded-xl border border-slate-700 focus-within:border-blue-500 focus-within:ring-1 focus-within:ring-blue-500 transition-all">
                <i class="fa-solid fa-link text-slate-500 ml-4"></i>
                <input type="text" id="videoUrl" placeholder="Paste YouTube URL here..." 
                    class="w-full bg-transparent border-none focus:ring-0 text-white placeholder-slate-500 py-4 px-3">
                <button onclick="analyzeVideo()" 
                    class="mr-2 bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-lg font-medium transition-colors">
                    Analyze
                </button>
            </div>
            <p id="errorMsg" class="text-red-400 text-sm mt-2 hidden"></p>
        </div>

        <div id="loading" class="hidden flex justify-center my-12">
            <div class="loader ease-linear rounded-full border-4 border-t-4 border-slate-700 h-12 w-12"></div>
        </div>

        <div id="results" class="hidden animate-fade-in-up">
            <div class="flex flex-col md:flex-row gap-6 mb-8">
                <div class="w-full md:w-1/3">
                    <img id="thumb" src="" alt="Thumbnail" class="w-full rounded-lg shadow-lg border border-slate-700">
                    <div class="mt-3 text-center">
                        <span id="duration" class="bg-slate-800 text-xs px-2 py-1 rounded text-slate-300"></span>
                    </div>
                </div>
                
                <div class="w-full md:w-2/3">
                    <h2 id="videoTitle" class="text-xl font-bold text-white mb-2 leading-tight"></h2>
                    <p id="channelName" class="text-blue-400 text-sm mb-4 font-medium"></p>
                    
                    <div class="space-y-4">
                        
                        <div class="bg-slate-800/40 rounded-lg p-4 border border-slate-700/50">
                            <h3 class="text-sm font-semibold text-slate-300 mb-3 flex items-center">
                                <i class="fa-solid fa-video-slash mr-2 text-purple-400"></i> Video (No Sound)
                            </h3>
                            <div id="videoContainer" class="grid grid-cols-2 sm:grid-cols-3 gap-2"></div>
                        </div>

                        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                            <div class="bg-slate-800/40 rounded-lg p-4 border border-slate-700/50">
                                <h3 class="text-sm font-semibold text-slate-300 mb-3 flex items-center">
                                    <i class="fa-solid fa-music mr-2 text-green-400"></i> Audio (MP3)
                                </h3>
                                <button onclick="downloadMedia('audio')" class="w-full bg-slate-700 hover:bg-green-600 hover:text-white text-slate-300 py-2 rounded text-sm transition-colors">
                                    Download Highest Quality
                                </button>
                            </div>

                            <div class="bg-slate-800/40 rounded-lg p-4 border border-slate-700/50">
                                <h3 class="text-sm font-semibold text-slate-300 mb-3 flex items-center">
                                    <i class="fa-solid fa-file-lines mr-2 text-yellow-400"></i> Transcript
                                </h3>
                                <button onclick="downloadMedia('transcript')" class="w-full bg-slate-700 hover:bg-yellow-600 hover:text-white text-slate-300 py-2 rounded text-sm transition-colors">
                                    Download Text
                                </button>
                            </div>
                        </div>

                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        let currentUrl = '';

        async function analyzeVideo() {
            const url = document.getElementById('videoUrl').value;
            const errorMsg = document.getElementById('errorMsg');
            const loading = document.getElementById('loading');
            const results = document.getElementById('results');

            if (!url) return;

            // Reset UI
            currentUrl = url;
            errorMsg.classList.add('hidden');
            results.classList.add('hidden');
            loading.classList.remove('hidden');

            try {
                const response = await fetch('/analyze', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({url: url})
                });
                
                const data = await response.json();

                if (data.error) {
                    throw new Error(data.error);
                }

                // Populate Data
                document.getElementById('thumb').src = data.thumbnail;
                document.getElementById('videoTitle').innerText = data.title;
                document.getElementById('channelName').innerText = data.uploader;
                document.getElementById('duration').innerText = data.duration_string;

                // Populate Video (No Sound) Options
                const videoContainer = document.getElementById('videoContainer');
                videoContainer.innerHTML = '';
                
                data.formats.forEach(fmt => {
                    const btn = document.createElement('button');
                    btn.className = 'bg-slate-700 hover:bg-purple-600 text-xs py-2 px-3 rounded text-slate-200 transition-colors truncate';
                    btn.innerText = `${fmt.resolution} (${fmt.ext})`;
                    btn.onclick = () => downloadMedia('video_nosound', fmt.format_id);
                    videoContainer.appendChild(btn);
                });

                loading.classList.add('hidden');
                results.classList.remove('hidden');

            } catch (err) {
                loading.classList.add('hidden');
                errorMsg.innerText = "Error: " + err.message;
                errorMsg.classList.remove('hidden');
            }
        }

        function downloadMedia(type, formatId = null) {
            let path = `/download?url=${encodeURIComponent(currentUrl)}&type=${type}`;
            if (formatId) {
                path += `&format_id=${formatId}`;
            }
            window.location.href = path;
        }
    </script>
</body>
</html>
"""

# --- BACKEND LOGIC ---

def clean_filename(title):
    return re.sub(r'[\\/*?:"<>|]', "", title)

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/analyze', methods=['POST'])
def analyze():
    url = request.json.get('url')
    if not url:
        return jsonify({'error': 'No URL provided'}), 400

    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # Filter formats: Video only (no audio)
            # We look for formats where vcodec is NOT none and acodec IS none
            formats = []
            for f in info['formats']:
                if f.get('vcodec') != 'none' and f.get('acodec') == 'none':
                    # Simplify resolution label
                    res = f.get('height')
                    if res:
                        formats.append({
                            'format_id': f['format_id'],
                            'resolution': f'{res}p',
                            'ext': f['ext'],
                            'filesize': f.get('filesize', 0)
                        })
            
            # Sort by resolution (high to low) and take unique resolutions to avoid clutter
            formats.sort(key=lambda x: int(x['resolution'].replace('p','')), reverse=True)
            # Deduplicate by resolution for cleaner UI
            seen_res = set()
            unique_formats = []
            for f in formats:
                if f['resolution'] not in seen_res:
                    unique_formats.append(f)
                    seen_res.add(f['resolution'])

            return jsonify({
                'title': info.get('title'),
                'uploader': info.get('uploader'),
                'thumbnail': info.get('thumbnail'),
                'duration_string': info.get('duration_string'),
                'formats': unique_formats[:6] # Limit to top 6 options
            })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download', methods=['GET'])
def download():
    url = request.args.get('url')
    dtype = request.args.get('type')
    fmt_id = request.args.get('format_id')
    
    if not url or not dtype:
        return "Missing parameters", 400

    try:
        # Common options
        ydl_opts = {
            'outtmpl': f'{DOWNLOAD_FOLDER}/%(title)s.%(ext)s',
            'quiet': True,
        }

        # 1. Download Video (No Sound)
        if dtype == 'video_nosound':
            ydl_opts['format'] = fmt_id

        # 2. Download Audio (MP3)
        elif dtype == 'audio':
            ydl_opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            })

        # 3. Download Transcript
        elif dtype == 'transcript':
            # Special handling for transcripts: we extract, don't download media
            ydl_opts.update({
                'skip_download': True,
                'writesubtitles': True,
                'writeautomaticsub': True,
                'subtitleslangs': ['en'],
                'outtmpl': f'{DOWNLOAD_FOLDER}/%(title)s', # Base name
            })
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True) # download=True here means download SUBS
                title = clean_filename(info['title'])
                
                # Check for the generated file (usually .en.vtt)
                # We try to find the file that was just created
                potential_files = [f for f in os.listdir(DOWNLOAD_FOLDER) if title in f and f.endswith('.vtt')]
                
                if potential_files:
                    file_path = os.path.join(DOWNLOAD_FOLDER, potential_files[0])
                    # Clean the VTT to plain text for user friendliness
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        # Simple regex to strip VTT timestamps/headers
                        text_content = re.sub(r'WEBVTT.*', '', content, flags=re.DOTALL)
                        text_content = re.sub(r'\d{2}:\d{2}:\d{2}\.\d{3}.*\n', '', text_content) # Remove timestamps
                        text_content = re.sub(r'<[^>]+>', '', text_content) # Remove tags
                        text_content = os.linesep.join([s for s in text_content.splitlines() if s.strip()]) # Remove empty lines
                    
                    # Send as plain text
                    return Response(
                        text_content,
                        mimetype="text/plain",
                        headers={"Content-disposition": f"attachment; filename={title}_transcript.txt"}
                    )
                else:
                    return "No English transcript found.", 404

        # EXECUTE DOWNLOAD (For Audio/Video)
        if dtype != 'transcript':
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                
                # If audio conversion happened, the extension changes
                if dtype == 'audio':
                    filename = os.path.splitext(filename)[0] + '.mp3'

                return send_file(filename, as_attachment=True)

    except Exception as e:
        return f"Error: {str(e)}", 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
