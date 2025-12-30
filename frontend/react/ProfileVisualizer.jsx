import React, { useCallback, useEffect } from 'react';
import ReactFlow, {
    MiniMap,
    Controls,
    Background,
    useNodesState,
    useEdgesState,
    addEdge,
} from 'reactflow';
import 'reactflow/dist/style.css';
import './ProfileVisualizer.css';

const initialNodes = [
    { id: '1', position: { x: 250, y: 0 }, data: { label: 'User' }, type: 'input' },
];
const initialEdges = [];

const ProfileVisualizer = ({ data, userName }) => {
    const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
    const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
    const [rfInstance, setRfInstance] = React.useState(null);
    const [layoutMode, setLayoutMode] = React.useState('circular');
    const [newItemIds, setNewItemIds] = React.useState(new Set());
    const [collapsedNodes, setCollapsedNodes] = React.useState(new Set());
    const previousDataRef = React.useRef({});

    // Update graph when new data comes in OR layout mode changes
    useEffect(() => {
        if (!data) {
            previousDataRef.current = {};
            return;
        }

        console.log('[ProfileVisualizer] Processing data update');

        // Create user node with dynamic name
        const initialNodes = [
            {
                id: '1',
                position: { x: 250, y: 0 },
                data: { label: userName || 'User' },
                type: 'input',
                style: {
                    fontSize: '20px',
                    fontWeight: 'bold',
                    padding: '10px'
                }
            },
        ];

        const newNodes = [...initialNodes];
        const newEdges = [];

        // Group by category, then subcategory (key)
        // Also build a map to track which items are new
        const hierarchy = {};
        const itemToNodeId = new Map(); // Maps "category|subcat|value" to node ID

        Object.entries(data).forEach(([category, items]) => {
            if (!hierarchy[category]) {
                hierarchy[category] = {};
            }
            items.forEach(item => {
                const subcat = item.key || 'その他';
                // Use original_value if normalization occurred, otherwise use value
                const value = item.original_value || item.value;

                if (!hierarchy[category][subcat]) {
                    hierarchy[category][subcat] = [];
                }
                const valIndex = hierarchy[category][subcat].length;
                hierarchy[category][subcat].push(value);

                // Store mapping
                const itemKey = `${category}|${subcat}|${value}`;
                const nodeId = `val-${category}-${subcat}-${valIndex}`;
                itemToNodeId.set(itemKey, nodeId);
            });
        });

        // Re-detect new items using the correct node IDs
        const correctNewIds = new Set();
        Object.entries(data).forEach(([category, items]) => {
            const prevCategoryData = previousDataRef.current[category] || [];

            items.forEach(item => {
                const subcat = item.key || 'その他';
                // Use original_value if normalization occurred, otherwise use value
                const value = item.original_value || item.value;

                // Check if this exact item existed before
                const existedBefore = prevCategoryData.some(prevItem => {
                    const prevSubcat = prevItem.key || 'その他';
                    const prevValue = prevItem.original_value || prevItem.value;
                    return prevSubcat === subcat && prevValue === value;
                });

                if (!existedBefore) {
                    const itemKey = `${category}|${subcat}|${value}`;
                    const nodeId = itemToNodeId.get(itemKey);
                    if (nodeId) {
                        correctNewIds.add(nodeId);
                        console.log('[ProfileVisualizer] NEW ITEM DETECTED:', nodeId, value);
                    }
                }
            });
        });

        // Filter out empty categories (only show categories with data)
        const categoryKeys = Object.keys(hierarchy).filter(cat => {
            const subcats = hierarchy[cat];
            // Check if category has any subcategories with values
            return Object.keys(subcats).length > 0 &&
                   Object.values(subcats).some(values => values.length > 0);
        });

        console.log('[ProfileVisualizer] Categories with data:', categoryKeys);

        if (layoutMode === 'circular') {
            // === CIRCULAR LAYOUT ===
            categoryKeys.forEach((category, catIndex) => {
                const categoryNodeId = `cat-${category}`;
                const angle1 = (catIndex / categoryKeys.length) * 2 * Math.PI;
                const radius1 = 200;
                const catX = 250 + radius1 * Math.cos(angle1);
                const catY = radius1 * Math.sin(angle1);

                newNodes.push({
                    id: categoryNodeId,
                    position: { x: catX, y: catY },
                    data: { label: category },
                    style: {
                        background: '#e0e7ff',
                        color: '#3730a3',
                        fontWeight: 'bold',
                        borderRadius: '50%',
                        width: 70,
                        height: 70,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontSize: '14px',
                        textAlign: 'center',
                        padding: '5px'
                    },
                    draggable: true
                });

                newEdges.push({
                    id: `edge-user-${category}`,
                    source: '1',
                    target: categoryNodeId,
                    style: { stroke: '#818cf8', strokeWidth: 2 }
                });

                // Level 2: Subcategories around Category
                const subcatKeys = Object.keys(hierarchy[category]);
                subcatKeys.forEach((subcategory, subIndex) => {
                    const subcatNodeId = `subcat-${category}-${subcategory}`;
                    const angle2 = angle1 + ((subIndex - (subcatKeys.length - 1) / 2) * 0.6);
                    const radius2 = 120;

                    newNodes.push({
                        id: subcatNodeId,
                        position: { x: radius2 * Math.cos(angle2), y: radius2 * Math.sin(angle2) },
                        data: { label: subcategory },
                        parentNode: categoryNodeId,
                        hidden: collapsedNodes.has(categoryNodeId),
                        style: {
                            background: '#ddd6fe',
                            color: '#5b21b6',
                            fontWeight: '600',
                            borderRadius: '50%',
                            width: 60,
                            height: 60,
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            fontSize: '13px',
                            textAlign: 'center',
                            padding: '5px'
                        },
                        draggable: true
                    });

                    newEdges.push({
                        id: `edge-${category}-${subcategory}`,
                        source: categoryNodeId,
                        target: subcatNodeId,
                        style: { stroke: '#a78bfa', strokeWidth: 1.5 }
                    });

                    // Level 3: Values around Subcategory
                    hierarchy[category][subcategory].forEach((value, valIndex) => {
                        const valNodeId = `val-${category}-${subcategory}-${valIndex}`;
                        const angle3 = angle2 + ((valIndex - (hierarchy[category][subcategory].length - 1) / 2) * 0.4);
                        const radius3 = 120;

                        const isNewItem = correctNewIds.has(valNodeId);
                        if (isNewItem) {
                            console.log('[ProfileVisualizer] Adding new-item class to:', valNodeId);
                        }

                        const nodeConfig = {
                            id: valNodeId,
                            position: { x: radius3 * Math.cos(angle3), y: radius3 * Math.sin(angle3) },
                            data: { label: value },
                            parentNode: subcatNodeId,
                            hidden: collapsedNodes.has(categoryNodeId) || collapsedNodes.has(subcatNodeId),
                            className: isNewItem ? 'new-item' : '',
                            draggable: true
                        };

                        // new-itemでない場合のみstyleを設定（CSSを優先）
                        if (!isNewItem) {
                            nodeConfig.style = {
                                background: '#ffffff',
                                border: '1px solid #e0e7ff',
                                borderRadius: '20px',
                                padding: '8px 12px',
                                fontSize: '13px'
                            };
                        }

                        newNodes.push(nodeConfig);

                        newEdges.push({
                            id: `edge-${subcategory}-${valIndex}`,
                            source: subcatNodeId,
                            target: valNodeId,
                            style: { stroke: '#c7d2fe' }
                        });
                    });
                });
            });
        } else {
            // === WATERFALL LAYOUT ===
            newNodes[0] = {
                id: '1',
                position: { x: 800, y: 50 },
                data: { label: userName || 'User' },
                type: 'input',
                style: {
                    fontSize: '20px',
                    fontWeight: 'bold',
                    padding: '10px'
                }
            };

            let totalSubcats = 0;
            categoryKeys.forEach(cat => {
                totalSubcats += Object.keys(hierarchy[cat]).length;
            });

            const totalWidth = Math.max(1600, totalSubcats * 200);
            const catSpacing = Math.max(250, totalWidth / Math.max(categoryKeys.length, 1));
            const startX = (totalWidth - (categoryKeys.length - 1) * catSpacing) / 2;

            categoryKeys.forEach((category, catIndex) => {
                const categoryNodeId = `cat-${category}`;
                const catX = startX + catIndex * catSpacing;
                const catY = 200;

                newNodes.push({
                    id: categoryNodeId,
                    position: { x: catX, y: catY },
                    data: { label: category },
                    style: {
                        background: '#e0e7ff',
                        color: '#3730a3',
                        fontWeight: 'bold',
                        borderRadius: '50%',
                        width: 70,
                        height: 70,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontSize: '14px',
                        textAlign: 'center',
                        padding: '5px'
                    },
                    draggable: true
                });

                newEdges.push({
                    id: `edge-user-${category}`,
                    source: '1',
                    target: categoryNodeId,
                    style: { stroke: '#818cf8', strokeWidth: 2 }
                });

                const subcatKeys = Object.keys(hierarchy[category]);

                // サブカテゴリーを水平に配置 / Arrange subcategories horizontally
                const subcatSpacingX = 200;  // 水平間隔（文字が読める間隔） / Horizontal spacing (readable distance)
                const subcatStartOffsetX = -((subcatKeys.length - 1) * subcatSpacingX) / 2;  // 中央揃え / Center align
                const subcatOffsetY = 150;  // 親から下の固定距離 / Fixed distance below parent

                subcatKeys.forEach((subcategory, subIndex) => {
                    const subcatNodeId = `subcat-${category}-${subcategory}`;
                    const subcatOffsetX = subcatStartOffsetX + subIndex * subcatSpacingX;  // 水平配置 / Horizontal layout

                    newNodes.push({
                        id: subcatNodeId,
                        position: { x: subcatOffsetX, y: subcatOffsetY },
                        data: { label: subcategory },
                        parentNode: categoryNodeId,
                        hidden: collapsedNodes.has(categoryNodeId),
                        style: {
                            background: '#ddd6fe',
                            color: '#5b21b6',
                            fontWeight: '600',
                            borderRadius: '50%',
                            width: 60,
                            height: 60,
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            fontSize: '13px',
                            textAlign: 'center',
                            padding: '5px'
                        },
                        draggable: true
                    });

                    newEdges.push({
                        id: `edge-${category}-${subcategory}`,
                        source: categoryNodeId,
                        target: subcatNodeId,
                        style: { stroke: '#a78bfa', strokeWidth: 1.5 }
                    });

                    const values = hierarchy[category][subcategory];

                    // 値を水平に配置 / Arrange values horizontally
                    const valSpacingX = 150;  // 水平間隔（文字が読める間隔） / Horizontal spacing (readable distance)
                    const valStartOffsetX = -((values.length - 1) * valSpacingX) / 2;  // 中央揃え / Center align
                    const valOffsetY = 150;  // サブカテゴリーから下の固定距離 / Fixed distance below subcategory

                    values.forEach((value, valIndex) => {
                        const valNodeId = `val-${category}-${subcategory}-${valIndex}`;
                        const valOffsetX = valStartOffsetX + valIndex * valSpacingX;  // 水平配置 / Horizontal layout

                        const isNewItem = correctNewIds.has(valNodeId);
                        if (isNewItem) {
                            console.log('[ProfileVisualizer] Adding new-item class to:', valNodeId);
                        }

                        const nodeConfig = {
                            id: valNodeId,
                            position: { x: valOffsetX, y: valOffsetY },
                            data: { label: value },
                            parentNode: subcatNodeId,
                            hidden: collapsedNodes.has(categoryNodeId) || collapsedNodes.has(subcatNodeId),
                            className: isNewItem ? 'new-item' : '',
                            draggable: true
                        };

                        // new-itemでない場合のみstyleを設定（CSSを優先）
                        if (!isNewItem) {
                            nodeConfig.style = {
                                background: '#ffffff',
                                border: '1px solid #e0e7ff',
                                borderRadius: '20px',
                                padding: '8px 12px',
                                fontSize: '13px'
                            };
                        }

                        newNodes.push(nodeConfig);

                        newEdges.push({
                            id: `edge-${subcategory}-${valIndex}`,
                            source: subcatNodeId,
                            target: valNodeId,
                            style: { stroke: '#c7d2fe' }
                        });
                    });
                });
            });
        }

        // Update previous data reference AFTER creating nodes
        previousDataRef.current = JSON.parse(JSON.stringify(data));

        // Set new item IDs immediately (before rendering)
        if (correctNewIds.size > 0) {
            console.log('[ProfileVisualizer] Setting new items for highlight:', Array.from(correctNewIds));
            setNewItemIds(correctNewIds);

            // Clear highlight after 2.5 seconds
            setTimeout(() => {
                console.log('[ProfileVisualizer] Clearing highlight');
                setNewItemIds(new Set());
            }, 2500);
        }

        // Update nodes and edges
        setNodes(newNodes);
        setEdges(newEdges);

        // Fit view only when there are NO new items (to avoid interfering with highlight animation)
        if (rfInstance && correctNewIds.size === 0) {
            setTimeout(() => {
                rfInstance.fitView({
                    padding: layoutMode === 'waterfall' ? 0.15 : 0.2,
                    duration: 0,
                    maxZoom: layoutMode === 'waterfall' ? 0.8 : 1.2,
                    minZoom: 0.3
                });
            }, 100);
        }
    }, [data, layoutMode, userName, collapsedNodes, setNodes, setEdges, rfInstance]);

    const onConnect = useCallback((params) => setEdges((eds) => addEdge(params, eds)), [setEdges]);

    const onNodeClick = useCallback((event, node) => {
        if (node.id.startsWith('cat-') || node.id.startsWith('subcat-')) {
            setCollapsedNodes(prev => {
                const newSet = new Set(prev);
                if (newSet.has(node.id)) {
                    newSet.delete(node.id);
                } else {
                    newSet.add(node.id);
                }
                return newSet;
            });
        }
    }, []);

    const toggleLayout = useCallback(() => {
        setLayoutMode(prev => prev === 'circular' ? 'waterfall' : 'circular');
    }, []);

    const expandAll = useCallback(() => {
        setCollapsedNodes(new Set());
    }, []);

    return (
        <div style={{ width: '100%', height: '100%', position: 'relative' }}>
            <div className="absolute top-4 right-4 flex gap-2 z-10">
                <button
                    onClick={expandAll}
                    className="px-3 py-2 bg-green-500 text-white text-sm font-semibold rounded-lg hover:bg-green-600 transition-colors shadow-md"
                    title="すべて展開"
                >
                    📂 展開
                </button>
                <button
                    onClick={toggleLayout}
                    className="px-3 py-2 text-white text-sm font-semibold rounded-lg transition-colors shadow-md"
                    style={{
                        background: layoutMode === 'circular' ? '#4f46e5' : '#7c3aed',
                    }}
                    title={layoutMode === 'circular' ? '円形レイアウト（クリックでウォーターフォールに変更）' : 'ウォーターフォールレイアウト（クリックで円形に変更）'}
                >
                    {layoutMode === 'circular' ? '🔄 円形' : '🌊 ウォーターフォール'}
                </button>
            </div>
            <ReactFlow
                nodes={nodes}
                edges={edges}
                onNodesChange={onNodesChange}
                onEdgesChange={onEdgesChange}
                onConnect={onConnect}
                onNodeClick={onNodeClick}
                onInit={setRfInstance}
                fitView
            >
                <Controls />
                <MiniMap />
                <Background variant="dots" gap={12} size={1} />
            </ReactFlow>
        </div>
    );
};

export default ProfileVisualizer;
