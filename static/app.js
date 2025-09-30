// static/app.js
class VideoProcessorApp {
    constructor() {
        this.videoId = null;
        this.analysisResult = null;
        this.initializeEventListeners();
    }
    
    initializeEventListeners() {
        // File upload
        const uploadArea = document.getElementById('uploadArea');
        const fileInput = document.getElementById('fileInput');
        
        uploadArea.addEventListener('click', () => fileInput.click());
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });
        uploadArea.addEventListener('dragleave', () => {
            uploadArea.classList.remove('dragover');
        });
        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                this.handleFileSelect(files[0]);
            }
        });
        
        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                this.handleFileSelect(e.target.files[0]);
            }
        });
        
        // Analysis
        document.getElementById('analyzeBtn').addEventListener('click', () => {
            this.startAnalysis();
        });
        
        // Preview and process
        document.getElementById('blurStrength').addEventListener('input', (e) => {
            document.getElementById('blurValue').textContent = e.target.value;
        });
        
        document.getElementById('previewBtn').addEventListener('click', () => {
            this.generatePreview();
        });
        
        document.getElementById('processBtn').addEventListener('click', () => {
            this.processVideo();
        });
        
        // Download
        document.getElementById('downloadBtn').addEventListener('click', () => {
            this.downloadVideo();
        });
        
        document.getElementById('newVideoBtn').addEventListener('click', () => {
            this.resetApp();
        });
    }
    
    async handleFileSelect(file) {
        if (!file.type.startsWith('video/')) {
            this.showStatus('error', 'Please select a video file');
            return;
        }
        
        if (file.size > 500 * 1024 * 1024) {
            this.showStatus('error', 'File size must be less than 500MB');
            return;
        }
        
        this.showStatus('info', 'Uploading video...');
        
        try {
            const formData = new FormData();
            formData.append('file', file);
            
            const response = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                throw new Error(`Upload failed: ${response.statusText}`);
            }
            
            const result = await response.json();
            this.videoId = result.video_id;
            
            // Show file info
            const fileInfo = document.getElementById('fileInfo');
            fileInfo.innerHTML = `
                <strong>File:</strong> ${file.name}<br>
                <strong>Size:</strong> ${this.formatFileSize(file.size)}<br>
                <strong>Duration:</strong> ${result.video_info.duration.toFixed(1)}s<br>
                <strong>Resolution:</strong> ${result.video_info.width}x${result.video_info.height}
            `;
            fileInfo.classList.remove('hidden');
            
            // Setup original video
            const originalVideo = document.getElementById('originalVideo');
            const videoUrl = URL.createObjectURL(file);
            originalVideo.src = videoUrl;
            
            // Move to next step
            this.showStep('analyze');
            this.showStatus('success', 'Video uploaded successfully!');
            
        } catch (error) {
            this.showStatus('error', `Upload failed: ${error.message}`);
        }
    }
    
    async startAnalysis() {
        const analyzeBtn = document.getElementById('analyzeBtn');
        const progressContainer = document.getElementById('analyzeProgress');
        const statusDiv = document.getElementById('analyzeStatus');
        
        analyzeBtn.disabled = true;
        progressContainer.classList.remove('hidden');
        
        try {
            // Start analysis
            const response = await fetch(`/api/analyze/${this.videoId}`, {
                method: 'POST'
            });
            
            if (!response.ok) {
                throw new Error(`Analysis start failed: ${response.statusText}`);
            }
            
            // Poll for status
            this.pollAnalysisStatus();
            
        } catch (error) {
            analyzeBtn.disabled = false;
            this.showStatus('error', `Analysis failed: ${error.message}`, statusDiv);
        }
    }
    
    async pollAnalysisStatus() {
        const statusDiv = document.getElementById('analyzeStatus');
        const progressFill = document.getElementById('analyzeProgressFill');
        const progressText = document.getElementById('analyzeProgressText');
        
        const checkStatus = async () => {
            try {
                const response = await fetch(`/api/status/${this.videoId}`);
                if (!response.ok) return false;
                
                const status = await response.json();
                
                // Update progress
                progressFill.style.width = `${status.progress}%`;
                progressText.textContent = `${Math.round(status.progress)}% - ${status.message}`;
                
                if (status.status === 'analyzed') {
                    this.showStatus('success', 'Analysis completed!', statusDiv);
                    this.analysisResult = await this.getAnalysisResult();
                    this.showStep('process');
                    return true;
                } else if (status.status === 'error') {
                    this.showStatus('error', `Analysis failed: ${status.error}`, statusDiv);
                    document.getElementById('analyzeBtn').disabled = false;
                    return true;
                }
                
                // Continue polling
                setTimeout(checkStatus, 1000);
                return false;
                
            } catch (error) {
                this.showStatus('error', `Status check failed: ${error.message}`, statusDiv);
                document.getElementById('analyzeBtn').disabled = false;
                return true;
            }
        };
        
        checkStatus();
    }
    
    async getAnalysisResult() {
        const response = await fetch(`/api/analysis/${this.videoId}`);
        if (!response.ok) {
            throw new Error('Failed to get analysis results');
        }
        return await response.json();
    }
    
    async generatePreview() {
        const previewBtn = document.getElementById('previewBtn');
        const statusDiv = document.getElementById('processStatus');
        
        previewBtn.disabled = true;
        this.showStatus('info', 'Generating preview...', statusDiv);
        
        try {
            const blurStrength = parseInt(document.getElementById('blurStrength').value);
            
            const response = await fetch(`/api/preview/${this.videoId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    masks: this.analysisResult.faces_by_frame,
                    blur_strength: blurStrength,
                    preview_duration: 10
                })
            });
            
            if (!response.ok) {
                throw new Error(`Preview generation failed: ${response.statusText}`);
            }
            
            const result = await response.json();
            
            // Load preview video
            const previewVideo = document.getElementById('previewVideo');
            previewVideo.src = result.preview_url + '?t=' + new Date().getTime(); // Avoid cache
            
            this.showStatus('success', 'Preview generated!', statusDiv);
            previewBtn.disabled = false;
            
        } catch (error) {
            this.showStatus('error', `Preview failed: ${error.message}`, statusDiv);
            previewBtn.disabled = false;
        }
    }
    
    async processVideo() {
        const processBtn = document.getElementById('processBtn');
        const progressContainer = document.getElementById('processProgress');
        const statusDiv = document.getElementById('processStatus');
        
        processBtn.disabled = true;
        progressContainer.classList.remove('hidden');
        this.showStatus('info', 'Starting video processing...', statusDiv);
        
        try {
            const blurStrength = parseInt(document.getElementById('blurStrength').value);
            
            const response = await fetch(`/api/process/${this.videoId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    masks: this.analysisResult.faces_by_frame,
                    blur_strength: blurStrength
                })
            });
            
            if (!response.ok) {
                throw new Error(`Processing start failed: ${response.statusText}`);
            }
            
            // Poll for processing status
            this.pollProcessingStatus();
            
        } catch (error) {
            this.showStatus('error', `Processing failed: ${error.message}`, statusDiv);
            processBtn.disabled = false;
        }
    }
    
    async pollProcessingStatus() {
        const statusDiv = document.getElementById('processStatus');
        const progressFill = document.getElementById('processProgressFill');
        const progressText = document.getElementById('processProgressText');
        
        const checkStatus = async () => {
            try {
                const response = await fetch(`/api/status/${this.videoId}`);
                if (!response.ok) return false;
                
                const status = await response.json();
                
                // Update progress
                progressFill.style.width = `${status.progress}%`;
                progressText.textContent = `${Math.round(status.progress)}% - ${status.message}`;
                
                if (status.status === 'completed') {
                    this.showStatus('success', 'Video processing completed!', statusDiv);
                    this.showStep('download');
                    return true;
                } else if (status.status === 'error') {
                    this.showStatus('error', `Processing failed: ${status.error}`, statusDiv);
                    document.getElementById('processBtn').disabled = false;
                    return true;
                }
                
                // Continue polling
                setTimeout(checkStatus, 1000);
                return false;
                
            } catch (error) {
                this.showStatus('error', `Status check failed: ${error.message}`, statusDiv);
                document.getElementById('processBtn').disabled = false;
                return true;
            }
        };
        
        checkStatus();
    }
    
    downloadVideo() {
        if (this.videoId) {
            window.open(`/api/download/${this.videoId}`, '_blank');
        }
    }
    
    resetApp() {
        // Reset all state
        this.videoId = null;
        this.analysisResult = null;
        
        // Reset UI
        this.showStep('upload');
        
        // Clear file input
        document.getElementById('fileInput').value = '';
        document.getElementById('fileInfo').classList.add('hidden');
        document.getElementById('fileInfo').innerHTML = '';
        
        // Clear videos
        document.getElementById('originalVideo').src = '';
        document.getElementById('previewVideo').src = '';
        
        // Clear status messages
        document.getElementById('analyzeStatus').innerHTML = '';
        document.getElementById('processStatus').innerHTML = '';
        
        // Reset buttons
        document.getElementById('analyzeBtn').disabled = false;
        document.getElementById('previewBtn').disabled = false;
        document.getElementById('processBtn').disabled = false;
        
        // Reset progress bars
        document.getElementById('analyzeProgressFill').style.width = '0%';
        document.getElementById('analyzeProgressText').textContent = '0%';
        document.getElementById('processProgressFill').style.width = '0%';
        document.getElementById('processProgressText').textContent = '0%';
    }
    
    showStep(stepName) {
        // Hide all steps
        document.getElementById('step-upload').classList.add('hidden');
        document.getElementById('step-analyze').classList.add('hidden');
        document.getElementById('step-process').classList.add('hidden');
        document.getElementById('step-download').classList.add('hidden');
        
        // Show selected step
        document.getElementById(`step-${stepName}`).classList.remove('hidden');
    }
    
    showStatus(type, message, element = null) {
        const statusElement = element || document.getElementById('analyzeStatus');
        statusElement.innerHTML = `
            <div class="status ${type}">
                ${message}
            </div>
        `;
    }
    
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
}

// Initialize app when page loads
document.addEventListener('DOMContentLoaded', () => {
    new VideoProcessorApp();
});