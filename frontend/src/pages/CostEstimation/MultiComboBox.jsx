import { Check, ChevronsUpDown } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Command, CommandGroup, CommandItem } from '@/components/ui/command';
import {
	Popover,
	PopoverContent,
	PopoverTrigger,
} from '@/components/ui/popover';

export function MultiCombobox({ items, placeholder, value = [], onChange }) {
	const toggleValue = (val) => {
		const updated = value.includes(val)
			? value.filter((v) => v !== val)
			: [...value, val];
		onChange?.(updated);
	};

	return (
		<Popover>
			<PopoverTrigger asChild>
				<Button
					variant='outline'
					className='w-full flex justify-between items-start h-auto min-h-12 py-2 mt-2'
				>
					{value.length > 0 ? (
						<div className='flex flex-col items-start text-left'>
							{value.map((val) => {
								const item = items.find((i) => i.value === val);
								return (
									<span key={val}>{item?.label || val}</span>
								);
							})}
						</div>
					) : (
						<span className='text-muted-foreground'>
							{placeholder}
						</span>
					)}

					<ChevronsUpDown className='ml-2 h-4 w-4 shrink-0' />
				</Button>
			</PopoverTrigger>

			<PopoverContent className='w-55 p-0'>
				<Command>
					<CommandGroup>
						{items.map((item) => (
							<CommandItem
								key={item.value}
								onSelect={() => toggleValue(item.value)}
							>
								<Check
									className={`mr-2 h-4 w-4 ${
										value.includes(item.value)
											? 'opacity-100'
											: 'opacity-0'
									}`}
								/>
								{item.label}
							</CommandItem>
						))}
					</CommandGroup>
				</Command>
			</PopoverContent>
		</Popover>
	);
}
