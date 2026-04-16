import { useState, useEffect } from 'react';

// Import your configured api instance!
import api from '../../api';

const ImageIcon = () => (
	<svg
		width='18'
		height='18'
		viewBox='0 0 24 24'
		fill='none'
		stroke='currentColor'
		strokeWidth='1.5'
	>
		<rect x='3' y='3' width='18' height='18' rx='2' />
		<circle cx='8.5' cy='8.5' r='1.5' />
		<path d='m21 15-5-5L5 21' />
	</svg>
);

const HistoryIcon = () => (
	<svg
		width="20"
		height="20"
		viewBox="0 0 24 24"
		fill="none"
		stroke="currentColor"
		strokeWidth="2"
		strokeLinecap="round"
		strokeLinejoin="round"
	>
		<circle cx="12" cy="12" r="10" />
		<polyline points="12 6 12 12 16 14" />
	</svg>
);

const CloseIcon = () => (
	<svg 
		width="18" 
		height="18" 
		viewBox="0 0 24 24" 
		fill="none" 
		stroke="currentColor" 
		strokeWidth="2"
	>
		<path d="M18 6L6 18M6 6l12 12" />
	</svg>
);

const TYPE_MAP = {
	convert_to_3d: 'convert',
	cost_estimation: 'estimate',
};

const mapEntry = (entry) => ({
	id: entry.id,
	name: entry.filename,
	time: `#${entry.id}`,
	type: TYPE_MAP[entry.type] ?? entry.type,
	size: entry.image_base64
		? `~${Math.ceil((entry.image_base64.length * 0.75) / 1024)} KB`
		: '—',
	cost: null,
	thumb: entry.image_base64
		? `data:image/png;base64,${entry.image_base64}`
		: null,
});

const HistorySidebar = ({ userId: userIdProp, onItemClick }) => {
	const userId =
		userIdProp ?? Number(localStorage.getItem('user_id')) ?? null;
	const [history, setHistory] = useState([]);
	const [filter, setFilter] = useState('all');
	const [retryCount, setRetryCount] = useState(0);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState(null);
	const [isOpen, setIsOpen] = useState(false); // <-- Toggle state

	useEffect(() => {
		if (userId == null || !isOpen) return; // Only fetch if open

		let cancelled = false;

		const fetchHistory = async () => {
			setLoading(true);
			setError(null);
			try {
				const res = await api.get(`/history/user/${userId}`);
				if (!cancelled) setHistory(res.data.map(mapEntry));
			} catch (err) {
				if (!cancelled) {
					setError(
						err.response?.data?.detail ||
							err.response?.data?.error ||
							err.message ||
							'Failed to load history',
					);
				}
			} finally {
				if (!cancelled) setLoading(false);
			}
		};

		fetchHistory();
		return () => {
			cancelled = true;
		};
	}, [userId, retryCount, isOpen]);

	const filtered =
		filter === 'all' ? history : history.filter((h) => h.type === filter);

	return (
		<div className="relative">
			{/* Floating Toggle Button */}
			<button
				onClick={() => setIsOpen(!isOpen)}
				className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-200 rounded-lg shadow-sm hover:bg-gray-50 transition-colors text-sm font-medium text-gray-700"
			>
				<HistoryIcon />
				{isOpen ? 'Close History' : 'View History'}
			</button>

			{/* Collapsible Sidebar */}
			{isOpen && (
				<div className="absolute right-0 top-12 z-50 flex flex-col bg-white rounded-2xl border border-gray-200 shadow-xl w-80 max-h-[500px] overflow-hidden">
					{/* Header */}
					<div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
						<span className="font-bold text-[15px] text-[#0D121B]">
							Conversion History
						</span>
						<button 
							onClick={() => setIsOpen(false)}
							className="text-gray-400 hover:text-gray-600 p-1 rounded-md hover:bg-gray-100"
						>
							<CloseIcon />
						</button>
					</div>

					{/* Filter pills */}
					<div className="flex gap-2 px-4 py-2 border-b border-gray-100">
						{[
							{ key: 'all', label: 'All' },
						].map(({ key, label }) => (
							<button
								key={key}
								onClick={() => setFilter(key)}
								className={`text-[11px] px-3 py-1 rounded-full border transition-all cursor-pointer ${
									filter === key
										? 'bg-blue-50 border-blue-300 text-[#135BEC] font-medium'
										: 'border-gray-200 text-gray-500 hover:border-gray-300'
								}`}
							>
								{label}
							</button>
						))}
					</div>

					{/* List */}
					<div className="overflow-y-auto flex-1">
						{loading ? (
							<div className="flex flex-col items-center justify-center h-full py-10 text-gray-400">
								<p className="text-[13px]">Loading…</p>
							</div>
						) : error ? (
							<div className="flex flex-col items-center justify-center h-full py-10 gap-2">
								<p className="text-[13px] text-red-500">{error}</p>
								<button
									onClick={() => setRetryCount((c) => c + 1)}
									className="text-[11px] text-gray-400 hover:text-gray-600 underline"
								>
									Retry
								</button>
							</div>
						) : filtered.length === 0 ? (
							<div className="flex flex-col items-center justify-center h-full py-10 text-gray-400">
								<p className="text-[13px]">No conversions yet</p>
							</div>
						) : (
							filtered.map((item) => (
								<div
									key={item.id}
									onClick={() => {
										if (item.type === 'convert') {
											onItemClick?.(item);
											setIsOpen(false); // Auto-close on selection (optional)
										}
									}}
									className={`flex items-center gap-3 px-4 py-3 border-b border-gray-50 transition-colors ${
										item.type === 'convert'
											? 'hover:bg-gray-50 cursor-pointer'
											: 'opacity-60 cursor-default'
									}`}
								>
									{/* Thumbnail */}
									<div className="w-11 h-11 rounded-lg bg-gray-100 border border-gray-200 flex items-center justify-center flex-shrink-0 overflow-hidden text-gray-400">
										{item.thumb ? (
											<img
												src={item.thumb}
												alt={item.name}
												className="w-full h-full object-cover"
											/>
										) : (
											<ImageIcon />
										)}
									</div>

									{/* Info */}
									<div className="flex-1 min-w-0">
										<div className="text-[12px] font-medium text-[#0D121B] truncate">
											{item.name}
										</div>
										<div className="text-[11px] text-gray-400 mt-0.5">
											{item.time} · {item.size}
										</div>
									</div>

									{/* Badge */}
									<span
										className={`text-[10px] px-2 py-0.5 rounded-full whitespace-nowrap font-medium ${
											item.type === 'convert'
												? 'bg-green-100 text-green-800'
												: 'bg-amber-100 text-amber-800'
										}`}
									>
										{item.type === 'convert'
											? 'Converted'
											: 'Estimate'}
									</span>
								</div>
							))
						)}
					</div>
				</div>
			)}
		</div>
	);
};

export default HistorySidebar;