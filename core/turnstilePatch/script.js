function getRandomInt(min, max) {
    return Math.floor(Math.random() * (max - min + 1)) + min;
}

// 模拟真实的鼠标移动和点击
function simulateHumanBehavior() {
    let screenX = getRandomInt(800, 1200);
    let screenY = getRandomInt(400, 600);

    // 模拟鼠标位置
    Object.defineProperty(MouseEvent.prototype, 'screenX', { value: screenX });
    Object.defineProperty(MouseEvent.prototype, 'screenY', { value: screenY });

    // 自动点击turnstile验证框
    setInterval(() => {
        // 检查是否存在验证响应输入框
        const responseInput = document.querySelector('input[name="cf-turnstile-response"]');
        if (responseInput && !responseInput.value) {
            // 查找并点击验证框
            const iframes = document.querySelectorAll('iframe');
            iframes.forEach(iframe => {
                try {
                    if (iframe.src && iframe.src.includes('challenges.cloudflare.com')) {
                        const checkbox = iframe.contentDocument?.querySelector('.cf-turnstile-checkbox');
                        if (checkbox && !checkbox.checked) {
                            checkbox.click();
                            console.log('自动点击验证框');
                        }
                    }
                } catch (e) {
                    // 忽略跨域错误
                }
            });
        }
    }, 1000);
}

simulateHumanBehavior();

