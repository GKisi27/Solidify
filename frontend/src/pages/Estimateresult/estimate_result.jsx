import React from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import StraightenOutlinedIcon from '@mui/icons-material/StraightenOutlined';
import AttachMoneyOutlinedIcon from '@mui/icons-material/AttachMoneyOutlined';
import RadioButtonCheckedOutlinedIcon from '@mui/icons-material/RadioButtonCheckedOutlined';
import LayersOutlinedIcon from '@mui/icons-material/LayersOutlined';
import AccessTimeOutlinedIcon from '@mui/icons-material/AccessTimeOutlined';
import LocalShippingOutlinedIcon from '@mui/icons-material/LocalShippingOutlined';
import InventoryOutlinedIcon from '@mui/icons-material/InventoryOutlined';

export default function EstimateResults() {
	const { state } = useLocation();
	const navigate = useNavigate();

	if (!state?.results) {
		navigate('/', { replace: true });
		return null;
	}

	const { geometry, cost_results } = state.results;

	const geometryItems = [
		{
			label: 'Outer Perimeter',
			value: `${geometry.outer_perimeter_mm} mm`,
			icon: (
				<StraightenOutlinedIcon
					style={{ fontSize: 18, color: '#135BEC' }}
				/>
			),
		},
		{
			label: 'Inner Perimeter',
			value: `${geometry.inner_perimeter_mm} mm`,
			icon: (
				<StraightenOutlinedIcon
					style={{ fontSize: 18, color: '#135BEC' }}
				/>
			),
		},
		{
			label: 'Total Edge Length',
			value: `${geometry.total_edge_length_mm} mm`,
			icon: (
				<StraightenOutlinedIcon
					style={{ fontSize: 18, color: '#135BEC' }}
				/>
			),
		},
		{
			label: 'Thickness',
			value: `${geometry.thickness_mm} mm`,
			icon: (
				<LayersOutlinedIcon
					style={{ fontSize: 18, color: '#135BEC' }}
				/>
			),
		},
		{
			label: 'Total Holes / Cut-outs',
			value: geometry.hole_count,
			icon: (
				<RadioButtonCheckedOutlinedIcon
					style={{ fontSize: 18, color: '#135BEC' }}
				/>
			),
		},
	];

	return (
		<div
			style={{
				padding: '72px 36px 48px',
				background: '#F9FAFB',
				minHeight: '100vh',
				boxSizing: 'border-box',
				fontFamily: 'sans-serif',
			}}
		>
			{/* Header */}
			<div
				style={{
					display: 'flex',
					alignItems: 'center',
					justifyContent: 'space-between',
					marginBottom: '32px',
				}}
			>
				<div>
					<h2
						style={{
							margin: 0,
							fontSize: '22px',
							fontWeight: 700,
							color: '#0D121B',
						}}
					>
						Estimation Results
					</h2>
					<p
						style={{
							margin: '4px 0 0',
							fontSize: '13px',
							color: '#6B7280',
						}}
					>
						Review your geometry analysis and manufacturing cost
						breakdown.
					</p>
				</div>

				<button
					onClick={() =>
						navigate('/cost-estimation', { state: state })
					}
					style={{
						display: 'flex',
						alignItems: 'center',
						gap: '6px',
						padding: '9px 18px',
						fontSize: '13px',
						fontWeight: 500,
						border: '1px solid #E5E7EB',
						borderRadius: '10px',
						background: '#fff',
						cursor: 'pointer',
						color: '#0D121B',
					}}
				>
					<ArrowBackIcon style={{ fontSize: 16 }} />
					Back to Form
				</button>
			</div>

			{/* Geometry Card */}
			<div
				style={{
					background: '#fff',
					borderRadius: '16px',
					border: '1px solid #E5E7EB',
					marginBottom: '24px',
					overflow: 'hidden',
				}}
			>
				{/* Card Header */}
				<div
					style={{
						display: 'flex',
						alignItems: 'center',
						gap: '8px',
						padding: '14px 20px',
						borderBottom: '1px solid #E5E7EB',
					}}
				>
					<StraightenOutlinedIcon
						style={{ fontSize: 18, color: '#135BEC' }}
					/>
					<span
						style={{
							fontWeight: 600,
							fontSize: '14px',
							color: '#0D121B',
						}}
					>
						Geometry Analysis
					</span>
				</div>

				{/* Grid of geometry values */}
				<div
					style={{
						display: 'grid',
						gridTemplateColumns: 'repeat(3, 1fr)',
						gap: '1px',
						background: '#E5E7EB',
					}}
				>
					{geometryItems.map((item, i) => (
						<div
							key={i}
							style={{
								background: '#fff',
								padding: '20px 24px',
							}}
						>
							<div
								style={{
									display: 'flex',
									alignItems: 'center',
									gap: '6px',
									marginBottom: '8px',
								}}
							>
								{item.icon}
								<span
									style={{
										fontSize: '12px',
										color: '#6B7280',
										fontWeight: 500,
									}}
								>
									{item.label}
								</span>
							</div>
							<div
								style={{
									fontSize: '20px',
									fontWeight: 700,
									color: '#0D121B',
								}}
							>
								{item.value}
							</div>
						</div>
					))}
				</div>
			</div>

			{/* Cost Results */}
			<div
				style={{
					background: '#fff',
					borderRadius: '16px',
					border: '1px solid #E5E7EB',
					overflow: 'hidden',
				}}
			>
				{/* Card Header */}
				<div
					style={{
						display: 'flex',
						alignItems: 'center',
						gap: '8px',
						padding: '14px 20px',
						borderBottom: '1px solid #E5E7EB',
					}}
				>
					<AttachMoneyOutlinedIcon
						style={{ fontSize: 18, color: '#135BEC' }}
					/>
					<span
						style={{
							fontWeight: 600,
							fontSize: '14px',
							color: '#0D121B',
						}}
					>
						Processing Cost Breakdown
					</span>
				</div>

				{cost_results.length === 0 ? (
					<p
						style={{
							padding: '24px',
							color: '#6B7280',
							fontSize: '13px',
						}}
					>
						No compatible process/material combinations found.
					</p>
				) : (
					<table
						style={{ width: '100%', borderCollapse: 'collapse' }}
					>
						<thead>
							<tr style={{ background: '#F9FAFB' }}>
								{[
									{
										icon: (
											<LayersOutlinedIcon
												style={{ fontSize: 14 }}
											/>
										),
										label: 'Process',
									},
									{
										icon: (
											<InventoryOutlinedIcon
												style={{ fontSize: 14 }}
											/>
										),
										label: 'Material',
									},
									{
										icon: (
											<RadioButtonCheckedOutlinedIcon
												style={{ fontSize: 14 }}
											/>
										),
										label: 'Qty',
									},
									{
										icon: (
											<AttachMoneyOutlinedIcon
												style={{ fontSize: 14 }}
											/>
										),
										label: 'Processing Cost',
									},
									{
										icon: (
											<AttachMoneyOutlinedIcon
												style={{ fontSize: 14 }}
											/>
										),
										label: 'Total Cost',
									},
									{
										icon: (
											<AttachMoneyOutlinedIcon
												style={{ fontSize: 14 }}
											/>
										),
										label: 'Cost / Unit',
									},
								].map((col, i) => (
									<th
										key={i}
										style={{
											padding: '12px 16px',
											textAlign: 'left',
											fontSize: '12px',
											fontWeight: 600,
											color: '#6B7280',
											borderBottom: '1px solid #E5E7EB',
											whiteSpace: 'nowrap',
										}}
									>
										<div
											style={{
												display: 'flex',
												alignItems: 'center',
												gap: '5px',
											}}
										>
											{col.icon}
											{col.label}
										</div>
									</th>
								))}
							</tr>
						</thead>
						<tbody>
							{cost_results.map((r, i) => (
								<tr
									key={i}
									style={{
										borderBottom:
											i < cost_results.length - 1
												? '1px solid #F3F4F6'
												: 'none',
										transition: 'background 0.15s',
									}}
									onMouseEnter={(e) =>
										(e.currentTarget.style.background =
											'#F9FAFB')
									}
									onMouseLeave={(e) =>
										(e.currentTarget.style.background =
											'transparent')
									}
								>
									{/* Process badge */}
									<td style={{ padding: '16px' }}>
										<span
											style={{
												background: '#EEF3FD',
												color: '#135BEC',
												fontSize: '12px',
												fontWeight: 600,
												padding: '4px 10px',
												borderRadius: '20px',
												whiteSpace: 'nowrap',
											}}
										>
											{r.process}
										</span>
									</td>

									<td
										style={{
											padding: '16px',
											fontSize: '13px',
											fontWeight: 500,
											color: '#0D121B',
										}}
									>
										{r.material}
									</td>

									<td
										style={{
											padding: '16px',
											fontSize: '13px',
											color: '#374151',
										}}
									>
										{r.quantity}
									</td>

									{/* Processing cost */}
									<td style={{ padding: '16px' }}>
										<span
											style={{
												fontSize: '14px',
												fontWeight: 600,
												color: '#0D121B',
											}}
										>
											$
											{r.processing_cost_usd != null
												? r.processing_cost_usd.toFixed(
														4,
													)
												: '—'}
										</span>
									</td>

									{/* Total cost — highlighted */}
									<td style={{ padding: '16px' }}>
										<span
											style={{
												fontSize: '15px',
												fontWeight: 700,
												color: '#135BEC',
											}}
										>
											$
											{r.total_cost_usd != null
												? r.total_cost_usd.toFixed(4)
												: '—'}
										</span>
									</td>

									{/* Cost per unit */}
									<td style={{ padding: '16px' }}>
										<span
											style={{
												fontSize: '13px',
												color: '#374151',
											}}
										>
											$
											{r.cost_per_unit_usd != null
												? r.cost_per_unit_usd.toFixed(6)
												: '—'}
										</span>
									</td>
								</tr>
							))}
						</tbody>
					</table>
				)}
			</div>
		</div>
	);
}
