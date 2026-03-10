import { useState } from "react"
import { Check, ChevronsUpDown } from "lucide-react"

import { Button } from "@/components/ui/button"
import {
  Command,
  CommandGroup,
  CommandItem,
} from "@/components/ui/command"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"

export function MultiCombobox({ items, placeholder }) {
  const [values, setValues] = useState([])

  const toggleValue = (value) => {
    setValues((prev) =>
      prev.includes(value)
        ? prev.filter((v) => v !== value)
        : [...prev, value]
    )
  }

  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          className="w-full flex justify-between items-start h-auto min-h-12 py-2 mt-2"
        >
          {values.length > 0 ? (
            <div className="flex flex-col items-start text-left">
              {values.map((value) => {
                const item = items.find((i) => i.value === value)
                return (
                  <span key={value}>
                    {item?.label || value}
                  </span>
                )
              })}
            </div>
          ) : (
            <span className="text-muted-foreground ">{placeholder}</span>
          )}

          <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0" />
        </Button>
      </PopoverTrigger>

      <PopoverContent className="w-55 p-0">
        <Command>
          <CommandGroup>
            {items.map((item) => (
              <CommandItem
                key={item.value}
                onSelect={() => toggleValue(item.value)}
              >
                <Check
                  className={`mr-2 h-4 w-4 ${
                    values.includes(item.value)
                      ? "opacity-100"
                      : "opacity-0"
                  }`}
                />
                {item.label}
              </CommandItem>
            ))}
          </CommandGroup>
        </Command>
      </PopoverContent>
    </Popover>
  )
}