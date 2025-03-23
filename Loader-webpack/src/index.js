require('./styles.css');
const CONFIG = {
    FETCH_TIMEOUT: 5000,
    RETRY_DELAY: 1000,
    FRAGMENT_DELAY: 300,
    TOTAL_FRAGMENTS: 'fragments' // Será sobrescrito pelo index
};

class ContentLoader {
    constructor() {
        this.loadedFragmentsCount = 0;
        this.fragmentsContent = [];
        this.totalFragments = 0;
    }

    async loadIndexFile() {
        try {
            const response = await fetch('fragments/index.txt');
            if (!response.ok) throw new Error(`Falha ao carregar index: ${response.status}`);
            
            const text = await response.text();
            return this.parseIndexData(text);
        } catch (error) {
            console.error('Erro ao carregar index:', error);
            return null;
        }
    }

    parseIndexData(text) {
        const indexData = {};
        text.split('\n')
            .filter(line => line.trim())
            .forEach(line => {
                const [key, value] = line.split(':').map(part => part.trim());
                indexData[key] = (key === 'fragments' || key === 'filesize') 
                    ? Number(value) 
                    : value;
            });
        this.totalFragments = indexData.fragments;
        this.fragmentsContent = new Array(this.totalFragments).fill('');
        return indexData;
    }

    updateProgressBar() {
        const progressPercentage = (this.loadedFragmentsCount / this.totalFragments) * 100;
        document.getElementById('progress-bar').style.width = `${progressPercentage}%`;
    }

    async fetchFragment(index) {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), CONFIG.FETCH_TIMEOUT);

        try {
            const response = await fetch(`/fragments/fragment_${index}`, { signal: controller.signal });
            clearTimeout(timeoutId);
            
            if (!response.ok) throw new Error(`Erro no fragmento ${index}: ${response.status}`);
            
            const text = await response.text();
            this.fragmentsContent[index] = text;
            this.loadedFragmentsCount++;
            this.updateProgressBar();
            return true;
        } catch (error) {
            console.error(`Erro ao carregar fragmento ${index}:`, error);
            await this.delay(CONFIG.RETRY_DELAY);
            return this.fetchFragment(index); // Retry
        }
    }

    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    assembleContent() {
        const appContainer = document.getElementById('app-container');
        const loadingMessage = document.querySelector('.loading-message');
        loadingMessage.textContent = 'Iniciando o sistema...';

        try {
            const fullContent = this.fragmentsContent.join('');
            const doc = new DOMParser().parseFromString(fullContent, 'text/html');
            
            if (!doc.body) throw new Error('Falha ao parsear HTML');

            appContainer.innerHTML = '';
            this.appendStyles(doc);
            this.appendBodyContent(doc, appContainer);
            this.appendScripts(doc);
            this.forceLayoutRefresh(appContainer);
        } catch (error) {
            console.error('Erro ao montar conteúdo:', error);
            appContainer.innerHTML = this.getErrorMessage();
        }
    }

    appendStyles(doc) {
        doc.querySelectorAll('style').forEach(style => {
            const newStyle = document.createElement('style');
            newStyle.textContent = style.textContent;
            newStyle.dataset.dynamic = 'true';
            document.head.appendChild(newStyle);
        });
    }

    appendBodyContent(doc, container) {
        doc.body.childNodes.forEach(node => {
            container.appendChild(node.cloneNode(true));
        });
    }

    appendScripts(doc) {
        doc.querySelectorAll('script').forEach(script => {
            const newScript = document.createElement('script');
            if (script.src) {
                newScript.src = script.src;
                newScript.async = true;
            } else {
                newScript.textContent = script.textContent;
            }
            newScript.dataset.dynamic = 'true';
            newScript.onerror = () => console.error(`Erro no script: ${script.src || 'inline'}`);
            document.head.appendChild(newScript);
        });
    }

    forceLayoutRefresh(container) {
        window.dispatchEvent(new Event('resize'));
        setTimeout(() => {
            container.style.display = 'none';
            container.offsetHeight; // Force reflow
            container.style.display = 'block';
        }, 100);
    }

    getErrorMessage() {
        return `
            <div style="text-align: center; padding: 20px; color: #721c24;">
                Erro ao carregar o conteúdo. Por favor, recarregue a página.
            </div>
        `;
    }

    async loadAllFragments() {
        const indexData = await this.loadIndexFile();
        if (!indexData) return;

        for (let i = 0; i < this.totalFragments; i++) {
            await this.fetchFragment(i);
            await this.delay(CONFIG.FRAGMENT_DELAY);
        }
        this.assembleContent();
    }
}

window.addEventListener('load', () => {
    const loader = new ContentLoader();
    loader.loadAllFragments();
});