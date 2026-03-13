import React, { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import Box from './Box';
import { Input } from '@/components/ui/input';
import Lighting from './Lighting';
import { MultiCombobox } from './MultiComboBox';
import { Button } from '@/components/ui/button';
import Droplet from './Droplet';

const API_BASE = 'http://localhost:8000';

const CostEstimation = () => {
	const location = useLocation();
	const navigate = useNavigate();
	const imageFile = location.state?.file; 

	const processes = [
		{ label: 'Laser Cutting', value: 'Laser Cutting' },
		{ label: 'Waterjet Cutting', value: 'Waterjet Cutting' },
	];
	const materials = [
		{ label: 'Mild Steel', value: 'mild_steel' },
		{ label: 'Stainless Steel 304', value: 'stainless_steel' },
		{ label: 'Aluminum 6061', value: 'aluminum' },
		{ label: 'Acrylic (PMMA)', value: 'acrylic' },
		{ label: 'Plywood', value: 'plywood' },
		{ label: 'Carbon Fiber Composite', value: 'carbon_fiber' },
	];

	const [quantity, setQuantity] = useState('');
	const [thickness, setThickness] = useState('');
	const [selectedProcesses, setSelectedProcesses] = useState([]);
	const [selectedMaterials, setSelectedMaterials] = useState([]);

	const [laserSpeed, setLaserSpeed] = useState('');
	const [laserPower, setLaserPower] = useState('');
	const [laserElec, setLaserElec] = useState('');
	const [laserRate, setLaserRate] = useState('');

	const [wjSpeed, setWjSpeed] = useState('');
	const [wjPower, setWjPower] = useState('');
	const [wjElec, setWjElec] = useState('');
	const [wjRate, setWjRate] = useState('');

	const [loading, setLoading] = useState(false);
	const [error, setError] = useState(null);

	const autoLaserRate = () => {
		const rate = parseFloat(laserPower) * parseFloat(laserElec);
		if (!isNaN(rate)) setLaserRate(rate.toFixed(4));
	};
	const autoWjRate = () => {
		const rate = parseFloat(wjPower) * parseFloat(wjElec);
		if (!isNaN(rate)) setWjRate(rate.toFixed(4));
	};

	const handleSubmit = async () => {
		setError(null);

		if (!imageFile) {
			setError(
				'No image found. Please go back and upload an image first.',
			);
			return;
		}
		if (!quantity || !thickness) {
			setError('Please fill in quantity and thickness.');
			return;
		}
		if (selectedProcesses.length === 0) {
			setError('Please select at least one process.');
			return;
		}
		if (selectedMaterials.length === 0) {
			setError('Please select at least one material.');
			return;
		}

		setLoading(true);

		try {
			const formData = new FormData();
			formData.append('image', imageFile);
			formData.append('quantity', quantity);
			formData.append('user_input_thickness', thickness);
			formData.append('processes', selectedProcesses.join(','));
			formData.append('materials', selectedMaterials.join(','));

			if (selectedProcesses.includes('Laser Cutting')) {
				if (laserSpeed) formData.append('laser_speed', laserSpeed);
				if (laserPower) formData.append('laser_power', laserPower);
				if (laserElec) formData.append('laser_elec', laserElec);
				if (laserRate) formData.append('laser_rate', laserRate);
			}
			if (selectedProcesses.includes('Waterjet Cutting')) {
				if (wjSpeed) formData.append('wj_speed', wjSpeed);
				if (wjPower) formData.append('wj_power', wjPower);
				if (wjElec) formData.append('wj_elec', wjElec);
				if (wjRate) formData.append('wj_rate', wjRate);
			}

			const res = await fetch(`${API_BASE}/estimate`, {
				method: 'POST',
				body: formData,
			});

			console.log('Response status:', res);

			if (!res.ok) {
				const errData = await res.json();
				throw new Error(errData.detail || 'Estimation failed');
			}

			const data = await res.json();
			navigate('/estimate-results', { state: { results: data } });
		} catch (err) {
			setError(err.message || 'Something went wrong');
		} finally {
			setLoading(false);
		}
	};

	const showLaser = selectedProcesses.includes('Laser Cutting');
	const showWaterjet = selectedProcesses.includes('Waterjet Cutting');

	return (
		<div className='flex justify-center items-center mb-10'>
			<div>
				<div className='mt-25 font-bold text-[38px]'>
					Cost Estimation Form
				</div>
				<div className='text-[18px] text-[#64748B]'>
					Configure your manufacturing parameters to get an instant
					quote.
				</div>

				{!imageFile && ( 
					<div className='mt-4 p-4 bg-yellow-50 border border-yellow-200 rounded-xl text-yellow-800 text-[14px]'>
						No image uploaded. Please go back to the home page and
						upload an image first.
					</div>
				)}

				<div className='bg-white w-200 p-8 mt-5 border rounded-xl'>
					<div className='flex items-center gap-3'>
						<Box />
						<div className='font-bold text-2xl'>
							General Requirements
						</div>
					</div>

					<div className='flex justify-between items-center gap-10'>
						<div>
							<div className='pt-5 text-[20px] font-semibold'>
								Quantity (Units)
							</div>
							<Input
								id='quantity'
								placeholder='e.g. 500'
								type='number'
								className='w-[320px] h-14 mt-2'
								value={quantity}
								onChange={(e) => setQuantity(e.target.value)}
								required
							/>
						</div>
						<div>
							<div className='pt-5 text-[20px] font-semibold'>
								Thickness (mm)
							</div>
							<Input
								id='thickness'
								placeholder='e.g. 5'
								type='number'
								className='w-[320px] h-14 mt-2'
								value={thickness}
								onChange={(e) => setThickness(e.target.value)}
								required
							/>
						</div>
					</div>

					<div className='pt-8 text-[20px] font-semibold'>
						Select Processes
					</div>
					<MultiCombobox
						items={processes}
						placeholder='Select processes'
						value={selectedProcesses}
						onChange={setSelectedProcesses}
						className='pt-5'
					/>
					<br />
					<div className='text-[14px] text-[#64748B]'>
						Hold Ctrl (Cmd on Mac) to select multiple processes.
					</div>

					<div className='pt-6 text-[20px] font-semibold'>
						Materials
					</div>
					<MultiCombobox
						items={materials}
						placeholder='Select materials'
						value={selectedMaterials}
						onChange={setSelectedMaterials}
						className='pt-5'
					/>

					{showLaser && (
						<div className='bg-[#135BEC]/7 border-[#135BEC]/20 rounded-xl p-6 mt-9'>
							<div className='flex items-center gap-4'>
								<Lighting />
								<div className='font-bold text-[20px]'>
									Laser Cutting Parameters
								</div>
							</div>
							<div className='grid grid-cols-2 justify-center items-center gap-20 pt-5'>
								<div className='flex flex-col gap-5'>
									<label className='text-[18px] font-semibold'>
										Laser Speed (mm/sec)
									</label>
									<Input
										placeholder='0.00'
										type='number'
										value={laserSpeed}
										onChange={(e) =>
											setLaserSpeed(e.target.value)
										}
										className='placeholder:text-lg'
									/>
								</div>
								<div className='flex flex-col gap-5'>
									<label className='text-[18px] font-semibold'>
										Laser Power (kW)
									</label>
									<Input
										placeholder='0.00'
										type='number'
										value={laserPower}
										onChange={(e) =>
											setLaserPower(e.target.value)
										}
										className='placeholder:text-lg'
									/>
								</div>
							</div>
							<div className='grid grid-cols-2 justify-center items-center gap-20 pt-5'>
								<div className='flex flex-col gap-5'>
									<label className='text-[18px] font-semibold'>
										Elec. Rate ($/kWh)
									</label>
									<Input
										placeholder='$ 0.00'
										type='number'
										value={laserElec}
										onChange={(e) =>
											setLaserElec(e.target.value)
										}
										className='placeholder:text-lg'
									/>
								</div>
								<div className='flex flex-col gap-5'>
									<label className='text-[18px] font-semibold'>
										Machine Rate ($/hr)
									</label>
									<div className='relative w-76'>
										<Input
											type='number'
											placeholder='$ 0.00'
											value={laserRate}
											onChange={(e) =>
												setLaserRate(e.target.value)
											}
											className='placeholder:text-lg pr-16'
										/>
										<Button
											type='button'
											onClick={autoLaserRate}
											className='absolute right-1 top-1/2 -translate-y-1/2 h-6 bg-[#cdd9f4] text-[#135BEC] hover:bg-[#cdd9f4]'
										>
											Auto
										</Button>
									</div>
								</div>
							</div>
						</div>
					)}

					{showWaterjet && (
						<div className='bg-[#135BEC]/7 border-[#135BEC]/20 rounded-xl p-6 mt-9'>
							<div className='flex items-center gap-4'>
								<Droplet />
								<div className='font-bold text-[20px]'>
									Waterjet Cutting Parameters
								</div>
							</div>
							<div className='grid grid-cols-2 justify-center items-center gap-20 pt-5'>
								<div className='flex flex-col gap-5'>
									<label className='text-[18px] font-semibold'>
										Waterjet Speed (mm/sec)
									</label>
									<Input
										placeholder='0.00'
										type='number'
										value={wjSpeed}
										onChange={(e) =>
											setWjSpeed(e.target.value)
										}
										className='placeholder:text-lg'
									/>
								</div>
								<div className='flex flex-col gap-5'>
									<label className='text-[18px] font-semibold'>
										Waterjet Power (kW)
									</label>
									<Input
										placeholder='0.00'
										type='number'
										value={wjPower}
										onChange={(e) =>
											setWjPower(e.target.value)
										}
										className='placeholder:text-lg'
									/>
								</div>
							</div>
							<div className='grid grid-cols-2 justify-center items-center gap-20 pt-5'>
								<div className='flex flex-col gap-5'>
									<label className='text-[18px] font-semibold'>
										Waterjet Elec. Rate ($/kWh)
									</label>
									<Input
										placeholder='$ 0.00'
										type='number'
										value={wjElec}
										onChange={(e) =>
											setWjElec(e.target.value)
										}
										className='placeholder:text-lg'
									/>
								</div>
								<div className='flex flex-col gap-5'>
									<label className='text-[18px] font-semibold'>
										Waterjet Machine Rate ($/hr)
									</label>
									<div className='relative w-76'>
										<Input
											type='number'
											placeholder='$ 0.00'
											value={wjRate}
											onChange={(e) =>
												setWjRate(e.target.value)
											}
											className='placeholder:text-lg pr-16'
										/>
										<Button
											type='button'
											onClick={autoWjRate}
											className='absolute right-1 top-1/2 -translate-y-1/2 h-6 bg-[#cdd9f4] text-[#135BEC] hover:bg-[#cdd9f4]'
										>
											Auto
										</Button>
									</div>
								</div>
							</div>
						</div>
					)}

					{error && (
						<div className='mt-6 p-4 bg-red-50 border border-red-200 rounded-xl text-red-700 text-[14px]'>
							{error}
						</div>
					)}

					<div className='pt-10 flex justify-center items-center'>
						<Button
							onClick={handleSubmit}
							disabled={loading || !imageFile} 
							className='bg-[#135BEC] text-white text-[18px] font-bold p-7 hover:cursor-pointer hover:bg-[#135BEC] disabled:opacity-50'
						>
							{loading ? 'Generating...' : 'Generate Estimates'}
						</Button>
					</div>
				</div>
			</div>
		</div>
	);
};

export default CostEstimation;
