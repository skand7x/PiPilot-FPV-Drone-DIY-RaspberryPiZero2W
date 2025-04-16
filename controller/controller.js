document.addEventListener('DOMContentLoaded', function() {
    // Elements
    const connectionStatus = document.getElementById('connection-status');
    const telemetry = document.getElementById('telemetry');
    
    // Joysticks
    const leftJoystick = document.getElementById('left-joystick');
    const rightJoystick = document.getElementById('right-joystick');
    const leftStick = document.getElementById('left-stick');
    const rightStick = document.getElementById('right-stick');
    
    // Buttons
    const btnStart = document.getElementById('btn-start');
    const btnSelect = document.getElementById('btn-select');
    const btnA = document.getElementById('btn-a');
    const btnB = document.getElementById('btn-b');
    
    // Controller state
    const controllerState = {
        left_x: 0.0,
        left_y: 0.0,
        right_x: 0.0,
        right_y: 0.0,
        start_pressed: false,
        back_pressed: false,
        a_pressed: false,
        b_pressed: false,
        x_pressed: false,
        y_pressed: false,
        lb_pressed: false,
        rb_pressed: false,
        lt_value: 0.0,
        rt_value: 0.0
    };
    
    // Connection status
    let connected = false;
    let updateInterval = null;
    
    // Check server status
    function checkStatus() {
        fetch('/status')
            .then(response => response.json())
            .then(data => {
                connected = data.connected;
                connectionStatus.textContent = `Status: ${connected ? 'Connected' : 'Disconnected'}`;
                connectionStatus.style.color = connected ? '#28a745' : '#dc3545';
                
                if (connected && !updateInterval) {
                    updateInterval = setInterval(sendControllerState, 50); // 20Hz update rate
                }
            })
            .catch(error => {
                connected = false;
                connectionStatus.textContent = 'Status: Error connecting to server';
                connectionStatus.style.color = '#dc3545';
                console.error('Error checking status:', error);
                
                if (updateInterval) {
                    clearInterval(updateInterval);
                    updateInterval = null;
                }
            });
    }
    
    // Send controller state to server
    function sendControllerState() {
        if (!connected) return;
        
        fetch('/update', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(controllerState)
        })
        .catch(error => {
            console.error('Error sending controller state:', error);
        });
        
        // Update telemetry display
        telemetry.textContent = `Left: (${controllerState.left_x.toFixed(2)}, ${controllerState.left_y.toFixed(2)}) Right: (${controllerState.right_x.toFixed(2)}, ${controllerState.right_y.toFixed(2)})`;
    }
    
    // Handle joysticks
    function setupJoystick(joystickEl, stickEl, xProp, yProp) {
        let active = false;
        let centerX, centerY, maxDistance;
        
        function updateJoystickPosition(x, y) {
            const rect = joystickEl.getBoundingClientRect();
            centerX = rect.left + rect.width / 2;
            centerY = rect.top + rect.height / 2;
            maxDistance = rect.width / 2 - stickEl.offsetWidth / 2;
            
            const deltaX = x - centerX;
            const deltaY = y - centerY;
            const distance = Math.min(Math.sqrt(deltaX * deltaX + deltaY * deltaY), maxDistance);
            const angle = Math.atan2(deltaY, deltaX);
            
            const stickX = distance * Math.cos(angle);
            const stickY = distance * Math.sin(angle);
            
            stickEl.style.transform = `translate(${stickX}px, ${stickY}px)`;
            
            // Update controller state (-1 to 1 range)
            controllerState[xProp] = parseFloat((stickX / maxDistance).toFixed(2));
            
            // Invert Y axis to match conventional joystick behavior (up is positive)
            controllerState[yProp] = parseFloat((-stickY / maxDistance).toFixed(2));
        }
        
        function resetJoystick() {
            stickEl.style.transform = 'translate(0px, 0px)';
            controllerState[xProp] = 0;
            controllerState[yProp] = 0;
        }
        
        // Mouse/Touch events for joystick
        function handleStart(e) {
            e.preventDefault();
            active = true;
            const x = e.type.includes('touch') ? e.touches[0].clientX : e.clientX;
            const y = e.type.includes('touch') ? e.touches[0].clientY : e.clientY;
            updateJoystickPosition(x, y);
        }
        
        function handleMove(e) {
            if (!active) return;
            e.preventDefault();
            const x = e.type.includes('touch') ? e.touches[0].clientX : e.clientX;
            const y = e.type.includes('touch') ? e.touches[0].clientY : e.clientY;
            updateJoystickPosition(x, y);
        }
        
        function handleEnd(e) {
            e.preventDefault();
            active = false;
            resetJoystick();
        }
        
        // Add event listeners
        joystickEl.addEventListener('mousedown', handleStart);
        joystickEl.addEventListener('touchstart', handleStart);
        
        document.addEventListener('mousemove', handleMove);
        document.addEventListener('touchmove', handleMove, { passive: false });
        
        document.addEventListener('mouseup', handleEnd);
        document.addEventListener('touchend', handleEnd);
    }
    
    // Setup button event handlers
    function setupButton(buttonEl, stateProp) {
        function handleButtonDown(e) {
            e.preventDefault();
            buttonEl.classList.add('pressed');
            controllerState[stateProp] = true;
        }
        
        function handleButtonUp(e) {
            e.preventDefault();
            buttonEl.classList.remove('pressed');
            controllerState[stateProp] = false;
        }
        
        buttonEl.addEventListener('mousedown', handleButtonDown);
        buttonEl.addEventListener('touchstart', handleButtonDown);
        
        document.addEventListener('mouseup', handleButtonUp);
        buttonEl.addEventListener('touchend', handleButtonUp);
    }
    
    // Initialize the controller
    function init() {
        // Setup joysticks
        setupJoystick(leftJoystick, leftStick, 'left_x', 'left_y');
        setupJoystick(rightJoystick, rightStick, 'right_x', 'right_y');
        
        // Setup buttons
        setupButton(btnStart, 'start_pressed');
        setupButton(btnSelect, 'back_pressed');
        setupButton(btnA, 'a_pressed');
        setupButton(btnB, 'b_pressed');
        
        // Check connection status
        checkStatus();
        setInterval(checkStatus, 3000); // Check status every 3 seconds
    }
    
    // Initialize controller
    init();
}); 