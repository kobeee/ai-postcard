// 游戏状态
let gameState = {
    isRunning: false,
    isPaused: false,
    score: 0,
    highScore: localStorage.getItem('snakeHighScore') || 0
};

// 游戏配置
const GAME_CONFIG = {
    canvas: null,
    ctx: null,
    gridSize: 20,
    canvasSize: 400
};

// 蛇的初始状态
let snake = {
    body: [{ x: 200, y: 200 }],
    direction: { x: 0, y: 0 },
    nextDirection: { x: 0, y: 0 }
};

// 食物状态
let food = {
    x: 0,
    y: 0
};

// 游戏循环ID
let gameLoopId = null;

// DOM 元素引用
const elements = {};

// 初始化游戏
function initGame() {
    // 获取DOM元素
    elements.canvas = document.getElementById('gameCanvas');
    elements.ctx = elements.canvas.getContext('2d');
    elements.scoreElement = document.getElementById('score');
    elements.highScoreElement = document.getElementById('highScore');
    elements.gameOverDiv = document.getElementById('gameOver');
    elements.finalScoreElement = document.getElementById('finalScore');
    
    // 设置canvas配置
    GAME_CONFIG.canvas = elements.canvas;
    GAME_CONFIG.ctx = elements.ctx;
    
    // 显示最高分
    elements.highScoreElement.textContent = gameState.highScore;
    
    // 生成初始食物
    generateFood();
    
    // 绘制初始状态
    draw();
    
    // 绑定事件监听器
    bindEventListeners();
}

// 绑定事件监听器
function bindEventListeners() {
    // 键盘事件
    document.addEventListener('keydown', handleKeyPress);
    
    // 按钮事件
    document.getElementById('upBtn').addEventListener('click', () => changeDirection(0, -1));
    document.getElementById('downBtn').addEventListener('click', () => changeDirection(0, 1));
    document.getElementById('leftBtn').addEventListener('click', () => changeDirection(-1, 0));
    document.getElementById('rightBtn').addEventListener('click', () => changeDirection(1, 0));
    
    document.getElementById('startBtn').addEventListener('click', startGame);
    document.getElementById('pauseBtn').addEventListener('click', togglePause);
    document.getElementById('restartBtn').addEventListener('click', restartGame);
}

// 处理键盘按键
function handleKeyPress(event) {
    if (!gameState.isRunning && event.code !== 'Space') return;
    
    switch(event.code) {
        case 'ArrowUp':
        case 'KeyW':
            event.preventDefault();
            changeDirection(0, -1);
            break;
        case 'ArrowDown':
        case 'KeyS':
            event.preventDefault();
            changeDirection(0, 1);
            break;
        case 'ArrowLeft':
        case 'KeyA':
            event.preventDefault();
            changeDirection(-1, 0);
            break;
        case 'ArrowRight':
        case 'KeyD':
            event.preventDefault();
            changeDirection(1, 0);
            break;
        case 'Space':
            event.preventDefault();
            if (gameState.isRunning) {
                togglePause();
            } else {
                startGame();
            }
            break;
    }
}

// 改变蛇的方向
function changeDirection(x, y) {
    // 防止蛇反向移动
    if ((snake.direction.x !== 0 && x !== 0) || (snake.direction.y !== 0 && y !== 0)) {
        return;
    }
    
    snake.nextDirection = { x: x * GAME_CONFIG.gridSize, y: y * GAME_CONFIG.gridSize };
}

// 开始游戏
function startGame() {
    if (gameState.isRunning) return;
    
    resetGame();
    gameState.isRunning = true;
    gameState.isPaused = false;
    
    // 设置初始方向
    snake.direction = { x: GAME_CONFIG.gridSize, y: 0 };
    snake.nextDirection = { x: GAME_CONFIG.gridSize, y: 0 };
    
    gameLoop();
    
    // 更新按钮状态
    document.getElementById('startBtn').textContent = '游戏中...';
    document.getElementById('pauseBtn').disabled = false;
}

// 暂停/继续游戏
function togglePause() {
    if (!gameState.isRunning) return;
    
    gameState.isPaused = !gameState.isPaused;
    
    if (gameState.isPaused) {
        clearTimeout(gameLoopId);
        document.getElementById('pauseBtn').textContent = '继续';
    } else {
        gameLoop();
        document.getElementById('pauseBtn').textContent = '暂停';
    }
}

// 重置游戏
function resetGame() {
    snake.body = [{ x: 200, y: 200 }];
    snake.direction = { x: 0, y: 0 };
    snake.nextDirection = { x: 0, y: 0 };
    gameState.score = 0;
    updateScore();
    generateFood();
    elements.gameOverDiv.classList.add('hidden');
}

// 重新开始游戏
function restartGame() {
    gameState.isRunning = false;
    clearTimeout(gameLoopId);
    
    document.getElementById('startBtn').textContent = '开始游戏';
    document.getElementById('pauseBtn').textContent = '暂停';
    document.getElementById('pauseBtn').disabled = true;
    
    startGame();
}

// 游戏主循环
function gameLoop() {
    if (!gameState.isRunning || gameState.isPaused) return;
    
    update();
    draw();
    
    gameLoopId = setTimeout(gameLoop, 150); // 控制游戏速度
}

// 更新游戏状态
function update() {
    // 更新蛇的方向
    if (snake.nextDirection.x !== 0 || snake.nextDirection.y !== 0) {
        snake.direction = { ...snake.nextDirection };
    }
    
    // 移动蛇头
    const head = { ...snake.body[0] };
    head.x += snake.direction.x;
    head.y += snake.direction.y;
    
    // 检查墙壁碰撞
    if (head.x < 0 || head.x >= GAME_CONFIG.canvasSize || 
        head.y < 0 || head.y >= GAME_CONFIG.canvasSize) {
        gameOver();
        return;
    }
    
    // 检查自身碰撞
    for (let segment of snake.body) {
        if (head.x === segment.x && head.y === segment.y) {
            gameOver();
            return;
        }
    }
    
    snake.body.unshift(head);
    
    // 检查是否吃到食物
    if (head.x === food.x && head.y === food.y) {
        gameState.score += 10;
        updateScore();
        generateFood();
    } else {
        snake.body.pop();
    }
}

// 绘制游戏画面
function draw() {
    // 清空画布
    elements.ctx.fillStyle = '#f0f0f0';
    elements.ctx.fillRect(0, 0, GAME_CONFIG.canvasSize, GAME_CONFIG.canvasSize);
    
    // 绘制网格线
    elements.ctx.strokeStyle = '#e0e0e0';
    elements.ctx.lineWidth = 1;
    for (let i = 0; i <= GAME_CONFIG.canvasSize; i += GAME_CONFIG.gridSize) {
        elements.ctx.beginPath();
        elements.ctx.moveTo(i, 0);
        elements.ctx.lineTo(i, GAME_CONFIG.canvasSize);
        elements.ctx.stroke();
        
        elements.ctx.beginPath();
        elements.ctx.moveTo(0, i);
        elements.ctx.lineTo(GAME_CONFIG.canvasSize, i);
        elements.ctx.stroke();
    }
    
    // 绘制蛇
    snake.body.forEach((segment, index) => {
        if (index === 0) {
            // 蛇头
            elements.ctx.fillStyle = '#2e7d32';
            elements.ctx.fillRect(segment.x, segment.y, GAME_CONFIG.gridSize, GAME_CONFIG.gridSize);
            // 蛇头边框
            elements.ctx.strokeStyle = '#1b5e20';
            elements.ctx.lineWidth = 2;
            elements.ctx.strokeRect(segment.x, segment.y, GAME_CONFIG.gridSize, GAME_CONFIG.gridSize);
            
            // 绘制眼睛
            elements.ctx.fillStyle = '#ffffff';
            const eyeSize = 3;
            const eyeOffset = 5;
            elements.ctx.fillRect(segment.x + eyeOffset, segment.y + eyeOffset, eyeSize, eyeSize);
            elements.ctx.fillRect(segment.x + GAME_CONFIG.gridSize - eyeOffset - eyeSize, segment.y + eyeOffset, eyeSize, eyeSize);
        } else {
            // 蛇身
            elements.ctx.fillStyle = '#4caf50';
            elements.ctx.fillRect(segment.x + 1, segment.y + 1, GAME_CONFIG.gridSize - 2, GAME_CONFIG.gridSize - 2);
        }
    });
    
    // 绘制食物
    elements.ctx.fillStyle = '#f44336';
    elements.ctx.beginPath();
    elements.ctx.arc(
        food.x + GAME_CONFIG.gridSize / 2,
        food.y + GAME_CONFIG.gridSize / 2,
        GAME_CONFIG.gridSize / 2 - 2,
        0,
        2 * Math.PI
    );
    elements.ctx.fill();
    
    // 食物亮点
    elements.ctx.fillStyle = '#ffeb3b';
    elements.ctx.beginPath();
    elements.ctx.arc(
        food.x + GAME_CONFIG.gridSize / 2 - 3,
        food.y + GAME_CONFIG.gridSize / 2 - 3,
        2,
        0,
        2 * Math.PI
    );
    elements.ctx.fill();
}

// 生成食物
function generateFood() {
    let validPosition = false;
    
    while (!validPosition) {
        food.x = Math.floor(Math.random() * (GAME_CONFIG.canvasSize / GAME_CONFIG.gridSize)) * GAME_CONFIG.gridSize;
        food.y = Math.floor(Math.random() * (GAME_CONFIG.canvasSize / GAME_CONFIG.gridSize)) * GAME_CONFIG.gridSize;
        
        validPosition = true;
        
        // 确保食物不生成在蛇身上
        for (let segment of snake.body) {
            if (food.x === segment.x && food.y === segment.y) {
                validPosition = false;
                break;
            }
        }
    }
}

// 更新分数显示
function updateScore() {
    elements.scoreElement.textContent = gameState.score;
    
    if (gameState.score > gameState.highScore) {
        gameState.highScore = gameState.score;
        elements.highScoreElement.textContent = gameState.highScore;
        localStorage.setItem('snakeHighScore', gameState.highScore);
    }
}

// 游戏结束
function gameOver() {
    gameState.isRunning = false;
    clearTimeout(gameLoopId);
    
    elements.finalScoreElement.textContent = gameState.score;
    elements.gameOverDiv.classList.remove('hidden');
    
    document.getElementById('startBtn').textContent = '开始游戏';
    document.getElementById('pauseBtn').textContent = '暂停';
    document.getElementById('pauseBtn').disabled = true;
}

// 页面加载完成后初始化游戏
document.addEventListener('DOMContentLoaded', initGame);