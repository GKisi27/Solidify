import React, { useRef, useState } from 'react';
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
import { AiOutlineCloudUpload } from 'react-icons/ai';
import { FaWandMagicSparkles } from 'react-icons/fa6';
import { MdOutlineSpeed } from 'react-icons/md';
import { RxCountdownTimer } from 'react-icons/rx';
import { TbStack } from 'react-icons/tb';
import HistorySidebar from '../History/history_bar';

// Import your configured api instance!
// Adjust the relative path based on your folder structure
import api from '../../api';

const API_BASE = '/files';

const LandingPage = () => {
	const navigate = useNavigate();
	const inputRef = useRef(null);
	const abortControllerRef = useRef(null);

	const [selectedImage, setSelectedImage] = useState(null);
	const [selectedFile, setSelectedFile] = useState(null);
	const [confirmOpen, setConfirmOpen] = useState(false);
	const [processingOpen, setProcessingOpen] = useState(false);
	const [progress, setProgress] = useState(0);
	const [error, setError] = useState(null);
	const [processingMode, setProcessingMode] = useState(null);

	const [conversionHistory, setConversionHistory] = useState([]);
	const historyIdRef = useRef(1);

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
		{
			icon: <MdOutlineSpeed className='h-6 w-6 text-[#135BEC]' />,
			topic: 'Instant Processing',
			description:
				'High-speed cloud processing converts your images in seconds.',
		},
		{
			icon: <TbStack className='h-6 w-6 text-[#135BEC]' />,
			topic: 'Clean Geometry',
			description:
				'Optimized JSON output specifically formatted for Onshape Featurescripts.',
		},
		{
			icon: <RxCountdownTimer className='h-6 w-6 text-[#135BEC]' />,
			topic: 'Version Control',
			description:
				'Access your previous conversions anytime in the projects tab.',
		},
	];

	const handleCostEstimation = async () => {
		if (!selectedFile) return;
		setProcessingMode('estimate');
		setProcessingOpen(true);
		setProgress(0);
		setError(null);

		try {
			setProgress(100);
			addToHistory(selectedFile, 'estimate', selectedImage);
			setTimeout(() => {
				setProcessingOpen(false);
				navigate('/cost-estimation', { state: { file: selectedFile } });
			}, 500);
		} catch (err) {
			setError(err.message || 'Something went wrong');
			setProgress(0);
		}
	};

	const handleProceed = async () => {
		setConfirmOpen(false);
		setProcessingMode('convert');
		setProcessingOpen(true);
		setProgress(0);
		setError(null);

		try {
			const formData = new FormData();
			formData.append('file', selectedFile);

			setProgress(20);

			abortControllerRef.current = new AbortController();

			// Submit conversion job using our API instance
			const convertRes = await api.post(`${API_BASE}/convert`, formData, {
				signal: abortControllerRef.current.signal,
			});

			const convertData = convertRes.data;

			// Check if using Celery or ThreadPoolExecutor
			if (convertData.backend === 'celery' && convertData.task_id) {
				const taskId = convertData.task_id;
				let taskComplete = false;
				let historyId = null;

				setProgress(30);

				while (!taskComplete) {
					await new Promise((resolve) => setTimeout(resolve, 2000));

					const statusRes = await api.get(
						`${API_BASE}/task/${taskId}`,
					);
					const statusData = statusRes.data;

					if (statusData.status === 'PENDING') {
						setProgress(35);
					} else if (statusData.status === 'STARTED') {
						setProgress(50);
					} else if (statusData.ready) {
						taskComplete = true;

						if (statusData.success && statusData.history_id) {
							historyId = statusData.history_id;
							setProgress(90);
						} else {
							throw new Error(
								statusData.error || 'Conversion failed',
							);
						}
					}
				}

				// Fetch results using history_id via axios params
				const resultsRes = await api.get(`${API_BASE}/results`, {
					params: { history_id: historyId },
				});

				const resultsData = resultsRes.data;

				if (resultsData.status !== 'done')
					throw new Error(
						'Conversion not ready yet. Please try again.',
					);

				setProgress(100);
				addToHistory(selectedFile, 'convert', selectedImage);

				setTimeout(() => {
					setProcessingOpen(false);
					navigate('/results', {
						state: {
							convertedImage: resultsData.converted_image,
							docUrl: resultsData.doc_url,
							geminiJson: resultsData.gemini_json,
							convertedJson: resultsData.converted_json,
						},
					});
				}, 800);
			} else {
				// ThreadPoolExecutor mode - direct result
				const userId = localStorage.getItem('user_id');
				setProgress(90);

				const resultsRes = await api.get(`${API_BASE}/results`, {
					params: { user_id: userId },
				});

				const resultsData = resultsRes.data;

				if (resultsData.status !== 'done')
					throw new Error(
						'Conversion not ready yet. Please try again.',
					);

				setProgress(100);
				addToHistory(selectedFile, 'convert', selectedImage);

				setTimeout(() => {
					setProcessingOpen(false);
					navigate('/results', {
						state: {
							convertedImage: resultsData.converted_image,
							docUrl: resultsData.doc_url,
							geminiJson: resultsData.gemini_json,
							convertedJson: resultsData.converted_json,
						},
					});
				}, 800);
			}
		} catch (err) {
			// Axios throws a specific error name for cancelled requests
			if (err.name === 'CanceledError') {
				setError('Conversion cancelled');
			} else {
				// Handle both Axios structure and generic errors
				setError(
					err.response?.data?.detail ||
						err.response?.data?.error ||
						err.message ||
						'Something went wrong',
				);
			}
			setProgress(0);
		}
	};

	const handleHistoryClick = async (item) => {
		if (item.type !== 'convert') return;

		try {
			const res = await api.get(`/history/${item.id}`);
			const data = res.data;

			navigate('/results', {
				state: {
					convertedImage: data.converted_image,
					docUrl: data.doc_url,
					geminiJson: data.gemini_json,
					convertedJson: data.converted_json,
				},
			});
		} catch (err) {
			console.error(err);
		}
	};

	return (
		<div className='flex gap-6 px-8 py-6 min-h-screen'>
			{/* ── Main content ── */}
			<div className='flex-1 flex flex-col'>
				<div className='flex flex-col items-center mt-14'>
					<h1 className='font-bold text-[40px]'>
						Convert your images to 3D images
					</h1>
					<p className='text-[18px] text-[#0D121B] text-center mt-2'>
						Transform raster images into JSON for seamless Onshape
						Integration. Design
						<br />
						faster with automatic vectorization.
					</p>
				</div>

				<div className='flex justify-center items-center mt-10'>
					<Card className='flex justify-center items-center bg-white rounded-xl shadow-xl h-106 w-200 border-none'>
						<CardContent>
							{selectedImage ? (
								<div className='h-89.5 w-183.5 rounded-2xl relative'>
									<img
										src={selectedImage}
										className='w-full h-full object-contain'
										alt='preview'
									/>
									<div
										className='absolute bg-red-500 -top-2 -right-2 text-white h-7 w-7 flex justify-center items-center rounded-full cursor-pointer'
										onClick={() => {
											setSelectedImage(null);
											setSelectedFile(null);
											if (inputRef.current)
												inputRef.current.value = '';
										}}
									>
										X
									</div>
								</div>
							) : (
								<div className='flex flex-col gap-5 justify-center items-center border-2 border-dashed border-[#CFD7E7] bg-[#F6F6F8]/30 rounded-xl h-89.5 w-183.5'>
									<AiOutlineCloudUpload className='text-[#135BEC] w-14.5 h-12' />
									<div className='text-center'>
										<div className='font-bold text-[#0D121B] text-[20px]'>
											Upload your image
										</div>
										<div className='text-[#6B7280] text-[14px]'>
											Drag and drop PNG or JPEG, up to
											10MB
										</div>
									</div>
									<Button
										onClick={() =>
											inputRef.current?.click()
										}
										className='bg-[#135BEC] hover:bg-[#135BEC] text-white text-[14px] px-8 py-3 rounded-lg font-bold mt-2 cursor-pointer'
									>
										Select Image
									</Button>
									<input
										type='file'
										ref={inputRef}
										accept='image/*'
										className='hidden'
										onChange={(e) => {
											const file = e.target.files[0];
											if (file) {
												setSelectedFile(file);
												setSelectedImage(
													URL.createObjectURL(file),
												);
											}
										}}
									/>
								</div>
							)}
						</CardContent>
					</Card>
				</div>

				<div className='flex justify-center gap-5 mt-10'>
					<Dialog open={confirmOpen} onOpenChange={setConfirmOpen}>
						<DialogTrigger asChild>
							<Button
								disabled={!selectedImage}
								className='flex gap-2 text-white text-[18px] font-bold justify-center items-center bg-[#135BEC] hover:bg-[#135BEC] px-7 py-3 rounded-xl shadow-lg shadow-[#135BEC] w-70 h-14 cursor-pointer'
							>
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
							</DialogDescription>
							<DialogFooter>
								<Button
									variant='outline'
									onClick={() => setConfirmOpen(false)}
								>
									Cancel
								</Button>
								<Button
									className='bg-[#135BEC] text-white'
									onClick={handleProceed}
								>
									Proceed
								</Button>
							</DialogFooter>
						</DialogContent>
					</Dialog>
				</div>

				{/* Processing dialog */}
				<Dialog open={processingOpen} onOpenChange={setProcessingOpen}>
					<DialogContent
						className='max-w-lg'
						onInteractOutside={(e) => e.preventDefault()}
						onEscapeKeyDown={(e) => e.preventDefault()}
					>
						<DialogTitle className='sr-only'>
							Processing
						</DialogTitle>
						<div className='text-center space-y-6'>
							<img
								src='/Visual.png'
								alt='processing'
								className='mx-auto w-24'
							/>
							{error ? (
								<>
									<div className='text-[24px] font-bold text-red-600'>
										{processingMode === 'estimate'
											? 'Upload Failed'
											: 'Conversion Failed'}
									</div>
									<div className='text-[#6B7280] text-[14px]'>
										{error}
									</div>
									<Button
										className='bg-[#135BEC] text-white px-4 py-2 rounded-lg text-[14px] mt-6 cursor-pointer'
										onClick={() => {
											setProcessingOpen(false);
											setError(null);
										}}
									>
										Close
									</Button>
								</>
							) : (
								<>
									<div className='text-[24px] font-bold text-[#111827]'>
										{processingMode === 'estimate'
											? 'Uploading image...'
											: 'Analyzing image and generating 3D path...'}
									</div>
									<div className='text-[#6B7280] text-[14px]'>
										{processingMode === 'estimate'
											? "Your image is being uploaded. You'll be redirected shortly."
											: 'This may take a few moments depending on image complexity and mesh density.'}
									</div>
									<div className='bg-[#135BEC]/5 border border-[#135BEC]/10 px-5 py-6 rounded-xl mt-6'>
										<div className='flex justify-between mb-2'>
											<span className='font-medium text-[16px]'>
												{processingMode === 'estimate'
													? 'Uploading'
													: 'Processing Raster Data'}
											</span>
											<span className='text-[#135BEC] text-[14px] font-bold'>
												{progress}%
											</span>
										</div>
										<Progress
											value={progress}
											className='w-full [&>div]:bg-[#135BEC]'
										/>
									</div>
									<Button
										className='bg-[#135BEC] text-white px-4 py-2 rounded-lg text-[14px] mt-6 cursor-pointer'
										onClick={() => {
											if (abortControllerRef.current)
												abortControllerRef.current.abort();
											setProcessingOpen(false);
										}}
									>
										Cancel
									</Button>
								</>
							)}
						</div>
					</DialogContent>
				</Dialog>

				<div className='flex justify-center gap-6 mt-16 mb-12'>
					{features.map((item, index) => (
						<div
							key={index}
							className='bg-white w-60 p-6 border rounded-2xl'
						>
							{item.icon}
							<div className='font-bold mt-4'>{item.topic}</div>
							<div className='text-sm text-gray-500'>
								{item.description}
							</div>
						</div>
					))}
				</div>
			</div>

			{/* ── History Sidebar ── */}
			<div className='w-80 pt-14 flex-shrink-0'>
				<HistorySidebar onItemClick={handleHistoryClick} />
			</div>
		</div>
	);
};

export default LandingPage;
