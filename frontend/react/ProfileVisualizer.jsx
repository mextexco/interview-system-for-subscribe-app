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
    const previousDataLengthRef = React.useRef(0);
    const currentNewItemIdsRef = React.useRef(new Set());

    // Update graph when new data comes in OR layout mode changes
    useEffect(() => {
        if (!data) return;

        // Detect newly added items
        currentNewItemIdsRef.current = new Set();
        const totalItems = Object.values(data).flat().length;

        if (totalItems > previousDataLengthRef.current) {
            const newDataCount = totalItems - previousDataLengthRef.current;

            // Build hierarchy to get proper IDs
            const tempHierarchy = {};
            Object.entries(data).forEach(([category, items]) => {
                if (!tempHierarchy[category]) {
                    tempHierarchy[category] = {};
                }
                items.forEach(item => {
                    const subcat = item.key || 'その他';
                    const value = typeof item.value === 'object' ? item.value.original : item.value;
                    if (!tempHierarchy[category][subcat]) {
                        tempHierarchy[category][subcat] = [];
                    }
                    tempHierarchy[category][subcat].push(value);
                });
            });

            // Mark the newest items (last N items added)
            let itemCount = 0;
            let startMarking = false;
            Object.entries(tempHierarchy).forEach(([cat, subcats]) => {
                Object.entries(subcats).forEach(([subcat, values]) => {
                    values.forEach((value, valIndex) => {
                        itemCount++;
                        if (itemCount > previousDataLengthRef.current) {
                            startMarking = true;
                        }
                        if (startMarking) {
                            const valNodeId = `val-${cat}-${subcat}-${valIndex}`;
                            currentNewItemIdsRef.current.add(valNodeId);
                        }
                    });
                });
            });

            previousDataLengthRef.current = totalItems;
        } else if (!data || totalItems === 0) {
            previousDataLengthRef.current = 0;
        }

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

        // Helper to get existing position if available
        const getExistingPosition = (id, defaultPos) => {
            if (!rfInstance) return defaultPos;
            const existingNode = rfInstance.getNodes().find(n => n.id === id);
            return existingNode ? existingNode.position : defaultPos;
        };

        // Group by category, then subcategory (key)
        const hierarchy = {};
        Object.entries(data).forEach(([category, items]) => {
            if (!hierarchy[category]) {
                hierarchy[category] = {};
            }
            items.forEach(item => {
                const subcat = item.key || 'その他';
                const value = typeof item.value === 'object' ? item.value.original : item.value;

                if (!hierarchy[category][subcat]) {
                    hierarchy[category][subcat] = [];
                }
                hierarchy[category][subcat].push(value);
            });
        });

        const categoryKeys = Object.keys(hierarchy);

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

                        newNodes.push({
                            id: valNodeId,
                            position: { x: radius3 * Math.cos(angle3), y: radius3 * Math.sin(angle3) },
                            data: { label: value },
                            parentNode: subcatNodeId,
                            hidden: collapsedNodes.has(categoryNodeId) || collapsedNodes.has(subcatNodeId),
                            className: currentNewItemIdsRef.current.has(valNodeId) ? 'new-item' : '',
                            style: {
                                background: '#ffffff',
                                border: '1px solid #e0e7ff',
                                borderRadius: '20px',
                                padding: '8px 12px',
                                fontSize: '13px'
                            },
                            draggable: true
                        });

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
                const subcatSpacing = 200;
                const subcatStartOffset = - ((subcatKeys.length - 1) * subcatSpacing) / 2;

                subcatKeys.forEach((subcategory, subIndex) => {
                    const subcatNodeId = `subcat-${category}-${subcategory}`;
                    const subcatOffsetX = subcatStartOffset + subIndex * subcatSpacing;
                    const subcatOffsetY = 180;

                    newNodes.push({
                        id: subcatNodeId,
                        position: getExistingPosition(subcatNodeId, { x: subcatOffsetX, y: subcatOffsetY }),
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
                    const valSpacing = 120;
                    const valStartOffset = - ((values.length - 1) * valSpacing) / 2;

                    values.forEach((value, valIndex) => {
                        const valNodeId = `val-${category}-${subcategory}-${valIndex}`;
                        const valOffsetX = valStartOffset + valIndex * valSpacing;
                        const valOffsetY = 180;

                        newNodes.push({
                            id: valNodeId,
                            position: getExistingPosition(valNodeId, { x: valOffsetX, y: valOffsetY }),
                            data: { label: value },
                            parentNode: subcatNodeId,
                            hidden: collapsedNodes.has(categoryNodeId) || collapsedNodes.has(subcatNodeId),
                            className: currentNewItemIdsRef.current.has(valNodeId) ? 'new-item' : '',
                            style: {
                                background: '#ffffff',
                                border: '1px solid #e0e7ff',
                                borderRadius: '20px',
                                padding: '8px 12px',
                                fontSize: '13px'
                            },
                            draggable: true
                        });

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

        setNodes(newNodes);
        setEdges(newEdges);

        // Fit view
        if (rfInstance) {
            setTimeout(() => {
                if (currentNewItemIdsRef.current.size > 0) {
                    const newIds = Array.from(currentNewItemIdsRef.current);
                    const nodesToFocus = newNodes.filter(n => newIds.includes(n.id));

                    if (nodesToFocus.length > 0) {
                        const parentId = nodesToFocus[0].parentNode;
                        const parentNode = newNodes.find(n => n.id === parentId);

                        if (parentNode) {
                            rfInstance.fitView({
                                nodes: [{ id: parentId }, ...nodesToFocus.map(n => ({ id: n.id }))],
                                padding: 0.5,
                                duration: 1000,
                                maxZoom: 1.5,
                                minZoom: 0.5
                            });
                        } else {
                            rfInstance.fitView({
                                nodes: nodesToFocus.map(n => ({ id: n.id })),
                                padding: 0.5,
                                duration: 1000
                            });
                        }
                    } else {
                        rfInstance.fitView({
                            padding: layoutMode === 'waterfall' ? 0.15 : 0.2,
                            duration: 800,
                            maxZoom: layoutMode === 'waterfall' ? 0.8 : 1.2,
                            minZoom: 0.3
                        });
                    }

                    setTimeout(() => {
                        setNewItemIds(new Set(currentNewItemIdsRef.current));
                        setTimeout(() => {
                            setNewItemIds(new Set());
                        }, 2000);
                    }, 1100);

                } else {
                    rfInstance.fitView({
                        padding: layoutMode === 'waterfall' ? 0.15 : 0.2,
                        duration: 800,
                        maxZoom: layoutMode === 'waterfall' ? 0.8 : 1.2,
                        minZoom: 0.3
                    });
                }
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
