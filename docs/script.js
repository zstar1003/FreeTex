/**
 * 处理 Tab 切换逻辑
 * @param {Event} evt - 点击事件对象
 * @param {string} tabName - 要切换到的 Tab 的 ID
 */
function openTab(evt, tabName) {
    // 获取所有 Tab 内容和链接
    var i, tabcontent, tablinks;
    tabcontent = document.getElementsByClassName("tab-content");
    for (i = 0; i < tabcontent.length; i++) {
        tabcontent[i].style.display = "none"; // 隐藏所有 Tab 内容
        tabcontent[i].classList.remove('animate__fadeIn'); // 移除动画类
    }
    tablinks = document.getElementsByClassName("tab-link");
    for (i = 0; i < tablinks.length; i++) {
        tablinks[i].className = tablinks[i].className.replace(" active", ""); // 移除 active 类
    }

    // 显示当前 Tab，并添加 active 类
    const currentTab = document.getElementById(tabName);
    currentTab.style.display = "block";
    currentTab.classList.add('animate__fadeIn'); // 添加淡入动画
    evt.currentTarget.className += " active";
}

/**
 * 处理滚动时的动画效果
 */
function handleScrollAnimation() {
    const elementsToAnimateOnScroll = document.querySelectorAll('.content-section h2, .content-section p, .feature-item, .usage-tabs, .tab-content, #community p'); // 需要滚动触发的元素

    const observerOptions = {
        root: null, // 视口
        rootMargin: '0px',
        threshold: 0.1 // 元素可见 10% 时触发
    };

    // Intersection Observer 用于检测元素是否进入视口
    const observer = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                // 给进入视口的元素添加动画类
                entry.target.classList.add('animate-on-scroll', 'animated');
                // 触发一次后停止观察该元素
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);

    // 观察所有需要滚动触发动画的元素
    elementsToAnimateOnScroll.forEach(el => {
        // 初始化时添加基础类，但不添加触发动画的类
        el.classList.add('animate-on-scroll');
        observer.observe(el);
    });
}

/**
 * @function fetchAndRenderMarkdown
 * @description 异步获取 Markdown 文件内容并使用 Marked.js 将其渲染为 HTML。
 * @param {string} markdownPath - Markdown 文件的路径。
 * @param {string} containerId - 用于显示渲染后 HTML 的容器元素的 ID。
 */
async function fetchAndRenderMarkdown(markdownPath, containerId) {
    const container = document.getElementById(containerId);
    if (!container) {
        console.error(`Container element with id "${containerId}" not found.`);
        return;
    }

    try {
        const response = await fetch(markdownPath);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const markdownText = await response.text();
        const htmlContent = marked.parse(markdownText); // 使用 marked.parse()
        container.innerHTML = htmlContent;
    } catch (error) {
        console.error('Error fetching or rendering Markdown:', error);
        container.innerHTML = '<p style="color: red;">加载常见问题失败，请稍后重试。</p>';
    }
}

// DOM 加载完成后执行初始化操作
document.addEventListener('DOMContentLoaded', () => {
    // 初始化滚动动画
    handleScrollAnimation();

    // 确保默认标签页正确显示
    const defaultTab = document.querySelector('.tab-link.active');
    if (defaultTab) {
        const onclickAttr = defaultTab.getAttribute('onclick');
        const tabNameMatch = onclickAttr.match(/openTab\(event, '([^']+)'\)/);
        if (tabNameMatch && tabNameMatch[1]) {
            const defaultTabName = tabNameMatch[1];
            const defaultTabContent = document.getElementById(defaultTabName);
            if (defaultTabContent) {
                defaultTabContent.style.display = "block";
                defaultTabContent.classList.add('animate__fadeIn');
            }
        }
    }
    
    // 加载 FAQ Markdown 内容
    fetchAndRenderMarkdown('faq.md', 'faq-container');
    fetchAndRenderMarkdown('plan.md', 'dev-plan-container');
    
    // 初始化 AOS (如果使用)
    if (typeof AOS !== 'undefined') {
        AOS.init({
            duration: 800, // 动画持续时间 (毫秒)
            once: true, // 动画是否只播放一次
            offset: 50, // 触发动画的偏移量 (像素)
        });
    }
});