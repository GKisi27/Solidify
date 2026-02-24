import { Button } from '@/components/ui/button';
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
import React, { useRef, useState } from 'react';
import { AiOutlineCloudUpload } from 'react-icons/ai';
import { FaWandMagicSparkles } from 'react-icons/fa6';
import { MdOutlineSpeed } from 'react-icons/md';
import { RxCountdownTimer } from 'react-icons/rx';
import { TbStack } from 'react-icons/tb';
import { Progress } from '@/components/ui/progress';
import { useNavigate } from 'react-router-dom';

const API_BASE = 'http://localhost:8001';

const LandingPage = () => {
	const navigate = useNavigate();
	const inputRef = useRef(null);

	const [selectedImage, setSelectedImage] = useState(null);
	const [selectedFile, setSelectedFile] = useState(null);
	const [confirmOpen, setConfirmOpen] = useState(false);
	const [processingOpen, setProcessingOpen] = useState(false);
	const [progress, setProgress] = useState(0);
	const [error, setError] = useState(null);

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

	const handleProceed = async () => {
		setConfirmOpen(false);
		setProcessingOpen(true);
		setProgress(0);
		setError(null);

		try {
			// Step 1: Upload → get image_id
			const formData = new FormData();
			formData.append('file', selectedFile);

			setProgress(20);
			const uploadRes = await fetch(`${API_BASE}/upload`, {
				method: 'POST',
				body: formData,
			});

			if (!uploadRes.ok) throw new Error('Upload failed');

			const { image_id } = await uploadRes.json();
			setProgress(40);

			// Step 2: Convert → poll progress visually
			const progressInterval = setInterval(() => {
				setProgress((prev) => (prev < 90 ? prev + 5 : prev));
			}, 400);

			const convertRes = await fetch(
				`${API_BASE}/convert?image_id=${image_id}`,
				{
					method: 'POST',
				},
			);

			clearInterval(progressInterval);

			if (!convertRes.ok) throw new Error('Conversion failed');

			// Parse JSON (not .text()) to get image_id back
			const convertData = await convertRes.json();
			setProgress(100);

			// Step 3: Navigate to results with imageId in state
			setTimeout(() => {
				setProcessingOpen(false);
				navigate('/results', {
					state: { imageId: convertData.image_id },
				});
			}, 800);
		} catch (err) {
			setError(err.message || 'Something went wrong');
			setProgress(0);
		}
	};

	return (
		<>
			<div className='flex flex-col items-center mt-20'>
				<div className='font-bold text-[40px]'>
					Convert your images to 3D images{' '}
				</div>
				<div className='text-[18px] text-[#0D121B] text-center'>
					Transform raster images into JSON for seamless Onshape
					Integration. Design
					<br />
					faster with automatic vectorization.
				</div>
			</div>

			<div className='flex justify-center items-center mt-15'>
				<Card className='flex justify-center items-center bg-[#FFFFFF] rounded-xl shadow-xl h-106 w-200 border-none'>
					<CardContent>
						{selectedImage ? (
							<div className='h-89.5 w-183.5 rounded-2xl relative'>
								<img
									src={selectedImage}
									className='w-full h-full object-cover'
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
								<div>
									<AiOutlineCloudUpload className='text-[#135BEC] w-14.5 h-12' />
								</div>
								<div className='flex flex-col items-center justify-center'>
									<div className='font-bold text-[#0D121B] text-[20px]'>
										Upload your image
									</div>
									<div className='text-[#6B7280] text-[14px]'>
										Drag and drop PNG or JPEG, up to 10MB
									</div>
								</div>

								<Button
									onClick={() => inputRef.current?.click()}
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

			<div className='flex justify-center mt-15'>
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

			{/* Processing / error dialog */}
			<Dialog open={processingOpen} onOpenChange={setProcessingOpen}>
				<DialogContent
					className='max-w-lg'
					aria-describedby={undefined}
				>
					<DialogTitle className='sr-only'>Processing</DialogTitle>
					<div className='text-center space-y-6'>
						<img
							src='/Visual.png'
							alt='processing'
							className='mx-auto w-24'
						/>

						{error ? (
							<>
								<div className='text-[24px] font-bold text-red-600'>
									Conversion Failed
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
									Analyzing image and generating 3D path...
								</div>
								<div className='text-[#6B7280] text-[14px]'>
									This may take a few moments depending on
									image complexity and mesh density.
								</div>

								<div className='bg-[#135BEC]/5 border border-[#135BEC]/10 px-5 py-6 rounded-xl mt-6'>
									<div className='flex justify-between mb-2'>
										<span className='font-medium text-[16px]'>
											Processing Raster Data
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
									onClick={() => setProcessingOpen(false)}
								>
									Cancel Processing
								</Button>
							</>
						)}
					</div>
				</DialogContent>
			</Dialog>

			<div className='flex justify-center gap-6 mt-20 mb-15'>
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
		</>
	);
};

export default LandingPage;
