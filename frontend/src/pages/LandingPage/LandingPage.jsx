import React, { useRef, useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import Money from './Money';
import { Card, CardContent } from '@/components/ui/card';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from '@/components/ui/dialog';
import { Progress } from '@/components/ui/progress';
import { AiOutlineCloudUpload, AiOutlineLoading3Quarters } from 'react-icons/ai';
import { FaWandMagicSparkles } from 'react-icons/fa6';
import { MdOutlineSpeed } from 'react-icons/md';
import { RxCountdownTimer } from 'react-icons/rx';
import { TbStack } from 'react-icons/tb';
import {
    PanelLeftOpen,
    PanelLeftClose,
    UploadCloud,
    FileText,
    X,
    Pencil,
} from 'lucide-react';
import HistorySidebar from '../History/history_bar';
import api from '../../api';

const API_BASE = '/files';

const LandingPage = () => {
    const navigate = useNavigate();
    const inputRef = useRef(null);
    const promptFileRef = useRef(null);
    const abortControllerRef = useRef(null);
    const taskIdRef = useRef(null);

    const [selectedImage, setSelectedImage] = useState(null);
    const [isDragging, setIsDragging] = useState(false);
    const [selectedFile, setSelectedFile] = useState(null);
    const [confirmOpen, setConfirmOpen] = useState(false);
    const [processingOpen, setProcessingOpen] = useState(false);
    const [loadingText, setLoadingText] = useState('');
    const [error, setError] = useState(null);
    const [processingMode, setProcessingMode] = useState(null);
    const [conversionHistory, setConversionHistory] = useState([]);
    const historyIdRef = useRef(1);

    // ── Prompt sidebar state ──────────────────────────────────────────
    const [sidebarOpen, setSidebarOpen] = useState(false);
    const [promptText, setPromptText] = useState('');
    const [promptFile, setPromptFile] = useState(null);          // { name, content }
    const [promptFileDragging, setPromptFileDragging] = useState(false);
    const [activePrompt, setActivePrompt] = useState(null);      // applied prompt shown as badge

    // ── Prompt file helpers ───────────────────────────────────────────
    const readPromptFile = (file) => {
        const ext = '.' + file.name.split('.').pop().toLowerCase();
        if (ext !== '.yml' && ext !== '.yaml') {
            alert('Only .yml files are supported.');
            return;
        }
        const reader = new FileReader();
        reader.onload = (e) => setPromptFile({ name: file.name, content: e.target.result });
        reader.readAsText(file);
    };

    const handlePromptFileDrop = (e) => {
        e.preventDefault();
        setPromptFileDragging(false);
        const file = e.dataTransfer.files[0];
        if (file) readPromptFile(file);
    };

    const handlePromptFileSelect = (e) => {
        const file = e.target.files[0];
        if (file) readPromptFile(file);
        e.target.value = '';
    };

    const applyPrompt = () => {
        if (!promptFile) return;
        setActivePrompt({ file: promptFile });
        setSidebarOpen(false);
    };

    const clearActivePrompt = () => {
        setActivePrompt(null);
        setPromptText('');
        setPromptFile(null);
    };

    // ── Image helpers (unchanged) ─────────────────────────────────────
    const handleImageFile = (file) => {
        if (file && file.type.startsWith('image/')) {
            setSelectedFile(file);
            setSelectedImage(URL.createObjectURL(file));
        } else {
            alert('Please upload a valid image file (PNG or JPEG).');
        }
    };

    useEffect(() => {
        const handlePaste = (e) => {
            const items = e.clipboardData?.items;
            if (!items) return;
            for (let i = 0; i < items.length; i++) {
                if (items[i].type.indexOf('image') !== -1) {
                    handleImageFile(items[i].getAsFile());
                    break;
                }
            }
        };
        window.addEventListener('paste', handlePaste);
        return () => window.removeEventListener('paste', handlePaste);
    }, []);

    const handleDragOver = (e) => { e.preventDefault(); setIsDragging(true); };
    const handleDragLeave = (e) => { e.preventDefault(); setIsDragging(false); };
    const handleDrop = (e) => {
        e.preventDefault();
        setIsDragging(false);
        if (e.dataTransfer.files?.length) {
            handleImageFile(e.dataTransfer.files[0]);
            e.dataTransfer.clearData();
        }
    };

    const addToHistory = (file, type, thumb) => {
        setConversionHistory((prev) => [
            {
                id: historyIdRef.current++,
                name: file.name,
                time: 'Just now',
                type,
                size: (file.size / 1048576).toFixed(1) + ' MB',
                cost: '$' + (Math.random() * 0.3 + 0.05).toFixed(2),
                thumb,
            },
            ...prev,
        ]);
    };

    const features = [
        { icon: <MdOutlineSpeed className='h-6 w-6 text-[#135BEC]' />, topic: 'Instant Processing', description: 'High-speed cloud processing converts your images in seconds.' },
        { icon: <TbStack className='h-6 w-6 text-[#135BEC]' />, topic: 'Clean Geometry', description: 'Optimized JSON output specifically formatted for Onshape Featurescripts.' },
        { icon: <RxCountdownTimer className='h-6 w-6 text-[#135BEC]' />, topic: 'Version Control', description: 'Access your previous conversions anytime in the projects tab.' },
    ];

    // ── Handlers (handleProceed passes activePrompt to results) ───────
    const handleCostEstimation = async () => {
        if (!selectedFile) return;
        setProcessingMode('estimate');
        setProcessingOpen(true);
        setLoadingText('Uploading image for estimation...');
        setError(null);
        try {
            addToHistory(selectedFile, 'estimate', selectedImage);
            setTimeout(() => {
                setProcessingOpen(false);
                navigate('/cost-estimation', { state: { file: selectedFile } });
            }, 1000);
        } catch (err) {
            setError(err.message || 'Something went wrong');
        }
    };

    const handleProceed = async () => {
        setConfirmOpen(false);
        setProcessingMode('convert');
        setProcessingOpen(true);
        setLoadingText('Uploading your image...');
        setError(null);

        try {
            const formData = new FormData();
            formData.append('file', selectedFile);
            // Attach active prompt if present
            if (activePrompt?.file?.content) formData.append('prompt_file_content', activePrompt.file.content);

            abortControllerRef.current = new AbortController();

            const convertRes = await api.post(`${API_BASE}/convert`, formData, {
                signal: abortControllerRef.current.signal,
            });
            const convertData = convertRes.data;

            if (convertData.backend === 'celery' && convertData.task_id) {
                const taskId = convertData.task_id;
                taskIdRef.current = taskId;
                let taskComplete = false;
                let historyId = null;
                setLoadingText('Initiating conversion task...');

                while (!taskComplete) {
                    await new Promise((r) => setTimeout(r, 2000));
                    const statusRes = await api.get(`${API_BASE}/task/${taskId}`);
                    const statusData = statusRes.data;

                    if (statusData.status === 'REVOKED') throw new Error('Task was cancelled');
                    if (statusData.status === 'PENDING') setLoadingText('Waiting in queue for resources...');
                    else if (statusData.status === 'STARTED') setLoadingText('Analyzing image and generating 3D paths (this may take a minute)...');
                    else if (statusData.ready) {
                        taskComplete = true;
                        if (statusData.success && statusData.history_id) {
                            historyId = statusData.history_id;
                            setLoadingText('Finalizing your 3D model...');
                        } else {
                            throw new Error(statusData.error || 'Conversion failed');
                        }
                    }
                }

                setLoadingText('Fetching final results...');
                const resultsRes = await api.get(`${API_BASE}/results`, { params: { history_id: historyId } });
                const resultsData = resultsRes.data;
                if (resultsData.status !== 'done') throw new Error('Conversion not ready yet. Please try again.');

                taskIdRef.current = null;
                addToHistory(selectedFile, 'convert', selectedImage);
                setLoadingText('Done! Redirecting...');
                setTimeout(() => {
                    setProcessingOpen(false);
                    navigate('/results', { state: { convertedImage: resultsData.converted_image, docUrl: resultsData.doc_url, geminiJson: resultsData.gemini_json, convertedJson: resultsData.converted_json } });
                }, 800);
            } else {
                setLoadingText('Processing image directly...');
                const userId = localStorage.getItem('user_id');
                const resultsRes = await api.get(`${API_BASE}/results`, { params: { user_id: userId } });
                const resultsData = resultsRes.data;
                if (resultsData.status !== 'done') throw new Error('Conversion not ready yet. Please try again.');
                addToHistory(selectedFile, 'convert', selectedImage);
                setLoadingText('Done! Redirecting...');
                setTimeout(() => {
                    setProcessingOpen(false);
                    navigate('/results', { state: { convertedImage: resultsData.converted_image, docUrl: resultsData.doc_url, geminiJson: resultsData.gemini_json, convertedJson: resultsData.converted_json } });
                }, 800);
            }
        } catch (err) {
            if (err.name === 'CanceledError') setError('Conversion cancelled');
            else setError(err.response?.data?.detail || err.response?.data?.error || err.message || 'Something went wrong');
        }
    };

    const handleHistoryClick = async (item) => {
        if (item.type !== 'convert') return;
        try {
            const res = await api.get(`/history/${item.id}`);
            const data = res.data;
            navigate('/results', { state: { convertedImage: data.converted_image, docUrl: data.doc_url, geminiJson: data.gemini_json, convertedJson: data.converted_json } });
        } catch (err) {
            console.error(err);
        }
    };

    return (
        <div className='relative min-h-screen flex'>

            {/* ── Prompt Sidebar ─────────────────────────────────────── */}
            <div
                className={`flex-shrink-0 bg-white border-r border-[#E5E7EB] flex flex-col transition-all duration-250 overflow-hidden ${
                    sidebarOpen ? 'w-72' : 'w-0'
                }`}
                style={{ height: '100vh', position: 'sticky', top: 0 }}
            >
                <div className='w-72 flex flex-col h-full'>

                    {/* Compact header — no wasted vertical space */}
                    <div className='flex items-center justify-between px-4 py-3 border-b border-[#E5E7EB] flex-shrink-0'>
                        <span className='text-sm font-semibold text-[#0D121B]'>Prompt</span>
                        <button
                            onClick={() => setSidebarOpen(false)}
                            className='w-6 h-6 flex items-center justify-center rounded border border-[#E5E7EB] text-gray-400 hover:bg-gray-100 transition'
                        >
                            <X size={12} />
                        </button>
                    </div>

                    {/* Scrollable body */}
                    <div className='flex flex-col flex-1 overflow-y-auto p-4 gap-3 min-h-0'>

                        {/* Drop zone */}
                        <div
                            onDragOver={(e) => { e.preventDefault(); setPromptFileDragging(true); }}
                            onDragLeave={() => setPromptFileDragging(false)}
                            onDrop={handlePromptFileDrop}
                            onClick={() => promptFileRef.current?.click()}
                            className={`flex flex-col items-center gap-2 border-2 border-dashed rounded-xl py-5 px-3 cursor-pointer transition-colors ${
                                promptFileDragging
                                    ? 'border-[#135BEC] bg-[#135BEC]/5'
                                    : 'border-[#CFD7E7] hover:border-[#135BEC] hover:bg-[#135BEC]/5'
                            }`}
                        >
                            <UploadCloud size={22} className='text-[#135BEC]' />
                            <div className='text-center'>
                                <p className='text-xs text-gray-500'>
                                    Drag & drop a file, or{' '}
                                    <span className='text-[#135BEC] font-medium'>browse</span>
                                </p>
                                <p className='text-[11px] text-gray-400 mt-0.5'>.yml only</p>
                            </div>
                            <input
                                type='file'
                                ref={promptFileRef}
                                accept='.yml,.yaml'
                                className='hidden'
                                onChange={handlePromptFileSelect}
                            />
                        </div>

                        {/* File chip */}
                        {promptFile && (
                            <div className='flex items-center gap-2 bg-[#F3F4F6] border border-[#E5E7EB] rounded-lg px-3 py-2 text-xs'>
                                <FileText size={13} className='text-[#135BEC] flex-shrink-0' />
                                <span className='flex-1 truncate text-[#0D121B]'>{promptFile.name}</span>
                                <button onClick={() => setPromptFile(null)} className='text-gray-400 hover:text-gray-600'>
                                    <X size={12} />
                                </button>
                            </div>
                        )}

                        {/* Apply button — right below the drop zone */}
                        <button
                            onClick={applyPrompt}
                            disabled={!promptFile}
                            className='w-full bg-[#135BEC] hover:bg-[#135BEC]/90 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-semibold py-2 rounded-lg transition'
                        >
                            Apply prompt
                        </button>

                    </div>
                </div>
            </div>

            {/* ── Toggle button ──────────────────────────────────────── */}
            <button
                onClick={() => setSidebarOpen((o) => !o)}
                className='absolute top-20 left-0 z-50 flex items-center gap-1.5 bg-white border border-[#E5E7EB] border-l-0 rounded-r-lg px-2.5 py-2 text-xs font-medium text-[#135BEC] hover:bg-[#F3F4F6] transition-all duration-250 shadow-sm'
                style={{ left: sidebarOpen ? '288px' : '0px' }}
            >
                {sidebarOpen
                    ? <PanelLeftClose size={15} />
                    : <PanelLeftOpen size={15} />
                }
                {!sidebarOpen && 'Prompt'}
            </button>

            {/* ── Main content ───────────────────────────────────────── */}
            <div className='flex-1 relative px-8 py-6 flex flex-col'>
                <div className='flex-1 flex flex-col w-full max-w-7xl mx-auto items-center'>

                    {/* Active prompt badge */}
                    {activePrompt && (
                        <div className='self-start mt-2 mb-[-8px] flex items-center gap-2 bg-[#E6F1FB] border border-[#B5D4F4] text-[#185FA5] rounded-lg px-3 py-1.5 text-xs'>
                            <Pencil size={12} />
                            <span>
                                {activePrompt.file
                                    ? `${activePrompt.file.name} loaded as prompt`
                                    : 'Custom prompt active'}
                            </span>
                            <button onClick={clearActivePrompt} className='ml-1 text-[#185FA5] hover:text-[#0c4580]'>
                                <X size={11} />
                            </button>
                        </div>
                    )}

                    <div className='flex flex-col items-center mt-14 text-center'>
                        <h1 className='font-bold text-[40px] text-[#0D121B]'>
                            Convert your images to 3D images
                        </h1>
                        <p className='text-[18px] text-[#0D121B] mt-2'>
                            Transform raster images into JSON for seamless Onshape Integration. Design
                            <br />faster with automatic vectorization.
                        </p>
                    </div>

                    {/* Upload card */}
                    <div className='flex justify-center items-center mt-10'>
                        <Card className='flex justify-center items-center bg-white rounded-xl shadow-xl h-106 w-200 border-none'>
                            <CardContent>
                                {selectedImage ? (
                                    <div className='h-89.5 w-183.5 rounded-2xl relative'>
                                        <img src={selectedImage} className='w-full h-full object-contain' alt='preview' />
                                        <div
                                            className='absolute bg-red-500 -top-2 -right-2 text-white h-7 w-7 flex justify-center items-center rounded-full cursor-pointer hover:bg-red-600 transition'
                                            onClick={() => { setSelectedImage(null); setSelectedFile(null); if (inputRef.current) inputRef.current.value = ''; }}
                                        >X</div>
                                    </div>
                                ) : (
                                    <div
                                        onDragOver={handleDragOver}
                                        onDragLeave={handleDragLeave}
                                        onDrop={handleDrop}
                                        className={`flex flex-col gap-5 justify-center items-center border-2 border-dashed rounded-xl h-89.5 w-183.5 transition-colors ${
                                            isDragging ? 'border-[#135BEC] bg-[#135BEC]/10' : 'border-[#CFD7E7] bg-[#F6F6F8]/30'
                                        }`}
                                    >
                                        <AiOutlineCloudUpload className='text-[#135BEC] w-14.5 h-12' />
                                        <div className='text-center'>
                                            <div className='font-bold text-[#0D121B] text-[20px]'>Upload your image</div>
                                            <div className='text-[#6B7280] text-[14px]'>Drag and drop PNG or JPEG, paste from clipboard, or click to browse</div>
                                        </div>
                                        <Button onClick={() => inputRef.current?.click()} className='bg-[#135BEC] hover:bg-[#135BEC]/90 text-white text-[14px] px-8 py-3 rounded-lg font-bold mt-2 cursor-pointer'>
                                            Select Image
                                        </Button>
                                        <input type='file' ref={inputRef} accept='image/*' className='hidden' onChange={(e) => { handleImageFile(e.target.files[0]); e.target.value = ''; }} />
                                    </div>
                                )}
                            </CardContent>
                        </Card>
                    </div>

                    {/* Convert button */}
                    <div className='flex justify-center gap-5 mt-10'>
                        <Dialog open={confirmOpen} onOpenChange={setConfirmOpen}>
                            <DialogTrigger asChild>
                                <Button disabled={!selectedImage} className='flex gap-2 text-white text-[18px] font-bold justify-center items-center bg-[#135BEC] hover:bg-[#135BEC]/90 px-7 py-3 rounded-xl shadow-lg shadow-[#135BEC] w-70 h-14 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed'>
                                    <FaWandMagicSparkles />
                                    Convert to 3D JSON
                                </Button>
                            </DialogTrigger>
                            <DialogContent className='bg-white'>
                                <DialogHeader>
                                    <DialogTitle>Confirmation</DialogTitle>
                                </DialogHeader>
                                <DialogDescription className='text-xl mt-4'>
                                    Are you sure you want to convert this image?
                                    {activePrompt && (
                                        <span className='block text-sm text-[#185FA5] mt-2'>
                                            A custom prompt will be included.
                                        </span>
                                    )}
                                </DialogDescription>
                                <DialogFooter>
                                    <Button variant='outline' onClick={() => setConfirmOpen(false)}>Cancel</Button>
                                    <Button className='bg-[#135BEC] text-white hover:bg-[#135BEC]/90' onClick={handleProceed}>Proceed</Button>
                                </DialogFooter>
                            </DialogContent>
                        </Dialog>
                    </div>

                    {/* Processing dialog */}
                    <Dialog open={processingOpen} onOpenChange={setProcessingOpen}>
                        <DialogContent className='max-w-md bg-white' onInteractOutside={(e) => e.preventDefault()} onEscapeKeyDown={(e) => e.preventDefault()}>
                            <DialogTitle className='sr-only'>Processing</DialogTitle>
                            <div className='text-center flex flex-col items-center py-6 space-y-6'>
                                {error ? (
                                    <>
                                        <div className='bg-red-100 p-4 rounded-full'><div className='text-red-500 font-bold text-2xl'>X</div></div>
                                        <div className='text-[24px] font-bold text-red-600'>{processingMode === 'estimate' ? 'Upload Failed' : 'Conversion Failed'}</div>
                                        <div className='text-[#6B7280] text-[14px] px-4'>{error}</div>
                                        <Button className='bg-[#135BEC] text-white px-8 py-2 rounded-lg text-[14px] mt-6 cursor-pointer hover:bg-[#135BEC]/90' onClick={() => { setProcessingOpen(false); setError(null); }}>Close</Button>
                                    </>
                                ) : (
                                    <>
                                        <div className='relative flex justify-center items-center h-24 w-24'>
                                            <AiOutlineLoading3Quarters className='animate-spin text-[#135BEC] w-16 h-16 absolute' />
                                            <FaWandMagicSparkles className='text-[#135BEC] w-6 h-6 absolute animate-pulse' />
                                        </div>
                                        <div className='text-[24px] font-bold text-[#111827]'>{processingMode === 'estimate' ? 'Uploading...' : 'Processing Image'}</div>
                                        <div className='bg-[#135BEC]/5 border border-[#135BEC]/10 px-6 py-4 rounded-xl w-full'>
                                            <div className='text-[#135BEC] font-medium text-[16px] animate-pulse'>{loadingText}</div>
                                        </div>
                                        <Button variant='outline' className='text-[#6B7280] border-[#CFD7E7] px-8 py-2 rounded-lg text-[14px] mt-6 cursor-pointer hover:bg-gray-50' onClick={async () => {
                                            if (taskIdRef.current) {
                                                try { await api.delete(`${API_BASE}/task/${taskIdRef.current}`); } catch (e) { console.error(e); }
                                                taskIdRef.current = null;
                                            }
                                            if (abortControllerRef.current) abortControllerRef.current.abort();
                                            setProcessingOpen(false);
                                        }}>Cancel Process</Button>
                                    </>
                                )}
                            </div>
                        </DialogContent>
                    </Dialog>

                    {/* Feature cards */}
                    <div className='flex justify-center gap-6 mt-16 mb-12'>
                        {features.map((item, index) => (
                            <div key={index} className='bg-white w-60 p-6 border rounded-2xl shadow-sm hover:shadow-md transition-shadow'>
                                {item.icon}
                                <div className='font-bold mt-4 text-[#0D121B]'>{item.topic}</div>
                                <div className='text-sm text-gray-500 mt-2'>{item.description}</div>
                            </div>
                        ))}
                    </div>
                </div>

                <div className='absolute top-20 right-8 z-50'>
                    <HistorySidebar onItemClick={handleHistoryClick} />
                </div>
            </div>
        </div>
    );
};

export default LandingPage;