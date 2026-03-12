import React from 'react';
import ArchitectureOutlinedIcon from '@mui/icons-material/ArchitectureOutlined';
import DescriptionOutlinedIcon from '@mui/icons-material/DescriptionOutlined';
import ViewInArOutlinedIcon from '@mui/icons-material/ViewInArOutlined';
import FileDownloadOutlinedIcon from '@mui/icons-material/FileDownloadOutlined';
import { useLocation, useNavigate } from 'react-router-dom';

const card = {
	background: '#fff',
	borderRadius: '16px',
	border: '1px solid #E5E7EB',
	overflow: 'hidden',
};

const cardHeader = {
	display: 'flex',
	alignItems: 'center',
	gap: '8px',
	padding: '13px 18px',
	borderBottom: '1px solid #E5E7EB',
	background: '#fff',
};

export default function Result() {
	const { state } = useLocation();
	const navigate = useNavigate();

	// If no state passed (user accessed directly), redirect to landing
	if (!state) {
		navigate('/', { replace: true });
		return null;
	}

	const { convertedImage, docUrl, geminiJson, convertedJson } = state;

	// Utility to download JSON files
	const downloadJson = (data, filename) => {
		const blob = new Blob([JSON.stringify(data, null, 2)], {
			type: 'application/json',
		});
		const url = URL.createObjectURL(blob);
		const a = document.createElement('a');
		a.href = url;
		a.download = filename;
		a.click();
		URL.revokeObjectURL(url);
	};

	return (
		<div
			style={{
				padding: '72px 36px 36px',
				background: '#F9FAFB',
				minHeight: '100vh',
				boxSizing: 'border-box',
			}}
		>
			{/* Page header */}
			<div
				style={{
					display: 'flex',
					alignItems: 'center',
					justifyContent: 'space-between',
					marginBottom: '24px',
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
						Conversion Results
					</h2>
					<p
						style={{
							margin: '4px 0 0',
							fontSize: '13px',
							color: '#6B7280',
						}}
					>
						Observe and check your input image and the conversion.
					</p>
				</div>

				<div
					style={{
						display: 'flex',
						gap: '10px',
						alignItems: 'center',
					}}
				>
					<button
						onClick={() => navigate('/')}
						style={{
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
						← New Conversion
					</button>

					{docUrl && (
						<a
							href={docUrl}
							target='_blank'
							rel='noopener noreferrer'
							style={{
								padding: '9px 20px',
								fontSize: '13px',
								fontWeight: 600,
								background: '#135BEC',
								color: '#fff',
								borderRadius: '10px',
								textDecoration: 'none',
								whiteSpace: 'nowrap',
							}}
						>
							Open in Onshape ↗
						</a>
					)}
				</div>
			</div>

			{/* Main grid: 55% image | 45% JSON stack */}
			<div
				style={{
					display: 'grid',
					gridTemplateColumns: '55fr 45fr',
					gap: '20px',
					alignItems: 'start',
				}}
			>
				{/* LEFT — 3D image */}
				<div style={card}>
					<div style={cardHeader}>
						<ViewInArOutlinedIcon
							style={{ color: '#135BEC', fontSize: '18px' }}
						/>
						<span
							style={{
								fontWeight: 600,
								fontSize: '13px',
								color: '#0D121B',
							}}
						>
							Onshape 3D
						</span>
					</div>
					<div
						style={{
							padding: '20px',
							background: '#F6F6F8',
							display: 'flex',
							alignItems: 'center',
							justifyContent: 'center',
							minHeight: '380px',
						}}
					>
						{convertedImage ? (
							<img
								src={convertedImage}
								alt='Converted 3D'
								style={{
									maxWidth: '100%',
									maxHeight: '460px',
									objectFit: 'contain',
									borderRadius: '8px',
								}}
							/>
						) : (
							<p style={{ color: '#6B7280', fontSize: '13px' }}>
								No preview available
							</p>
						)}
					</div>
				</div>

				{/* RIGHT — two JSON panels stacked */}
				<div
					style={{
						display: 'flex',
						flexDirection: 'column',
						gap: '16px',
					}}
				>
					{/* Base Mesh JSON */}
					<div style={card}>
						<div
							style={{
								...cardHeader,
								justifyContent: 'space-between',
							}}
						>
							<div
								style={{
									display: 'flex',
									alignItems: 'center',
									gap: '8px',
								}}
							>
								<DescriptionOutlinedIcon
									style={{
										color: '#135BEC',
										fontSize: '18px',
									}}
								/>
								<span
									style={{
										fontWeight: 600,
										fontSize: '13px',
										color: '#0D121B',
									}}
								>
									Base Mesh JSON
								</span>
							</div>
							{geminiJson && (
								<button
									onClick={() =>
										downloadJson(
											geminiJson,
											'base-mesh.json',
										)
									}
									style={{
										display: 'flex',
										alignItems: 'center',
										gap: '4px',
										padding: '5px 11px',
										fontSize: '12px',
										fontWeight: 500,
										background: '#135BEC',
										color: '#fff',
										border: 'none',
										borderRadius: '8px',
										cursor: 'pointer',
									}}
								>
									<FileDownloadOutlinedIcon
										style={{ fontSize: '15px' }}
									/>
									Download
								</button>
							)}
						</div>
						{geminiJson ? (
							<pre
								style={{
									margin: 0,
									padding: '14px 16px',
									fontSize: '11.5px',
									lineHeight: '1.6',
									fontFamily: 'monospace',
									color: '#0D121B',
									background: '#F9FAFB',
									overflowY: 'auto',
									overflowX: 'auto',
									maxHeight: '260px',
								}}
							>
								{JSON.stringify(geminiJson, null, 2)}
							</pre>
						) : (
							<p
								style={{
									margin: 0,
									padding: '16px',
									color: '#6B7280',
									fontSize: '13px',
								}}
							>
								No data available.
							</p>
						)}
					</div>

					{/* Onshape Compatible JSON */}
					<div style={card}>
						<div
							style={{
								...cardHeader,
								justifyContent: 'space-between',
							}}
						>
							<div
								style={{
									display: 'flex',
									alignItems: 'center',
									gap: '8px',
								}}
							>
								<ArchitectureOutlinedIcon
									style={{
										color: '#135BEC',
										fontSize: '18px',
									}}
								/>
								<span
									style={{
										fontWeight: 600,
										fontSize: '13px',
										color: '#0D121B',
									}}
								>
									Onshape Compatible JSON
								</span>
							</div>
							{convertedJson && (
								<button
									onClick={() =>
										downloadJson(
											convertedJson,
											'onshape-compatible.json',
										)
									}
									style={{
										display: 'flex',
										alignItems: 'center',
										gap: '4px',
										padding: '5px 11px',
										fontSize: '12px',
										fontWeight: 500,
										background: '#135BEC',
										color: '#fff',
										border: 'none',
										borderRadius: '8px',
										cursor: 'pointer',
									}}
								>
									<FileDownloadOutlinedIcon
										style={{ fontSize: '15px' }}
									/>
									Download
								</button>
							)}
						</div>
						{convertedJson ? (
							<pre
								style={{
									margin: 0,
									padding: '14px 16px',
									fontSize: '11.5px',
									lineHeight: '1.6',
									fontFamily: 'monospace',
									color: '#0D121B',
									background: '#F9FAFB',
									overflowY: 'auto',
									overflowX: 'auto',
									maxHeight: '260px',
								}}
							>
								{JSON.stringify(convertedJson, null, 2)}
							</pre>
						) : (
							<p
								style={{
									margin: 0,
									padding: '16px',
									color: '#6B7280',
									fontSize: '13px',
								}}
							>
								No data available.
							</p>
						)}
					</div>
				</div>
			</div>
		</div>
	);
}
