import React from 'react';
import ReactDOM from 'react-dom/client';
import ProfileVisualizer from './ProfileVisualizer';

// グローバルに公開する関数
window.initProfileVisualizer = function(containerId) {
    const container = document.getElementById(containerId);
    if (!container) {
        console.error(`[ProfileVisualizer] Container #${containerId} not found`);
        return null;
    }

    const root = ReactDOM.createRoot(container);

    // データと状態を保持
    let currentData = {};
    let currentUserName = '-';

    // 描画関数
    function render() {
        try {
            root.render(
                <React.StrictMode>
                    <ProfileVisualizer
                        data={currentData}
                        userName={currentUserName}
                    />
                </React.StrictMode>
            );
        } catch (error) {
            console.error('[ProfileVisualizer] Render error:', error);
        }
    }

    // 初期描画
    render();

    console.log('[ProfileVisualizer] Initialized successfully');

    // 外部から呼び出せる更新関数を返す
    return {
        updateData: function(newData) {
            console.log('[ProfileVisualizer] updateData called with:', newData);
            currentData = newData;
            render();
        },
        updateUserName: function(name) {
            console.log('[ProfileVisualizer] updateUserName called with:', name);
            currentUserName = name;
            render();
        },
        update: function(data, userName) {
            console.log('[ProfileVisualizer] update called with data:', data, 'userName:', userName);
            currentData = data;
            currentUserName = userName || currentUserName;
            render();
        }
    };
};

console.log('[ProfileVisualizer] Module loaded, initProfileVisualizer available');
