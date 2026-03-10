import React from "react";
import Box from "./Box";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import Lighting from "./Lighting";
import { MultiCombobox } from "./MultiComboBox";
import { Button } from "@/components/ui/button";
import Droplet from "./Droplet";

const CostEstimation = () => {
  const processes = [
    { label: "Laser Cutting", value: "laserCutting" },
    { label: "Waterjet Cutting", value: "waterjetCutting" },
  ];
  const materials = [
    { label: "Mild Steel", value: "mildSteel" },
    { label: "Stainless Steel 304", value: "stainlessSteel" },
    { label: "Aluminum 6061", value: "aluminum" },
    { label: "Acrylic (PMMA)", value: "acrylic" },
    { label: "Plywood", value: "plywood" },
    { label: "Carbon Fiber Composite", value: "carbonfiber" },
  ];

  return (
    <div className="flex justify-center items-center mb-10">
      <div>
        <div className="mt-25 font-bold text-[38px]">Cost Estimation Form</div>
        <div className="text-[18px] text-[#64748B]">
          Configure your manufacturing parameters to get an instant quote.
        </div>
        <form className="bg-white w-200 p-8 mt-5 border rounded-xl">
          <div className="flex items-center gap-3">
            <Box />
            <div className="font-bold text-2xl">General Requirements</div>
          </div>


          <div className="flex justify-between items-center gap-10">
            <div>
              <div className="pt-5 text-[20px] font-semibold">Quantity(Units)</div>
          <Input
            id="quantity"
            placeholder="e.g. 500"
            type="number"
            className="w-[320px] h-14 mt-2"
            required
          />
          <br />
            </div>
          
          <div>
            <div className="pt-5 text-[20px] font-semibold">Thickness</div>
          <Input
            id="quantity"
            placeholder="e.g. 50"
            type="number"
            className="w-[320px] h-14 mt-2"
            required
          />
          <br />
          </div>
          
          </div>

          <div className="pt-8 text-[20px] font-semibold">Select Processes</div>
          <MultiCombobox
            items={processes}
            placeholder={"Select processes"}
            className="pt-5"
          />
          <br />
          <div className="text-[14px] text-[#64748B]">
            Hold Ctrl (Cmd on Mac) to select multiple processes.
          </div>

          <div className="pt-6 text-[20px] font-semibold">Materials</div>
          <MultiCombobox
            items={materials}
            placeholder={"Select materials"}
            className="pt-5 placeholder:text-lg"
          />

          <div className="bg-[#135BEC]/7 border-[#135BEC]/20 rounded-xl p-6 mt-9">
            <div className="flex items-center gap-4">
              <Lighting />
              <div className="font-bold text-[20px]">
                Laser Cutting Parameters
              </div>
            </div>

            <div className="grid grid-cols-2 justify-center items-center gap-20 pt-5">
              <div className="flex flex-col gap-5">
                <label className="text-[18px] font-semibold">
                  Laser Speed (mm/sec)
                </label>
                <Input
                  id="speed"
                  placeholder="0.00"
                  type="number"
                  required
                  className="placeholder:text-lg"
                />
              </div>

              <div className="flex flex-col gap-5">
                <label className="text-[18px] font-semibold">
                  Laser Power (kW)
                </label>
                <Input
                  id="speed"
                  placeholder="0.00"
                  type="number"
                  required
                  className="placeholder:text-lg"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 justify-center items-center gap-20 pt-5">
              <div className="flex flex-col gap-5">
                <label className="text-[18px] font-semibold">
                  Elec. Rate ($/kWh)
                </label>
                <Input
                  id="speed"
                  placeholder="$ 0.00"
                  type="number"
                  required
                  className="placeholder:text-lg"
                />
              </div>

              <div className="flex flex-col gap-5">
                <label className="text-[18px] font-semibold">
                  Machine Rate ($/hr)
                </label>

                <div className="relative w-76">
                  <Input
                    id="speed"
                    type="number"
                    placeholder="$ 0.00"
                    required
                    className="placeholder:text-lg pr-16"
                  />

                  <Button
                    type="button"
                    className="absolute right-1 top-1/2 -translate-y-1/2 h-6 bg-[#cdd9f4] text-[#135BEC] hover:bg-[#cdd9f4]"
                  >
                    Auto
                  </Button>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-[#135BEC]/7 border-[#135BEC]/20 rounded-xl p-6 mt-9">
            <div className="flex items-center gap-4">
              <Droplet />
              <div className="font-bold text-[20px]">
                Waterjet Cutting Parameters
              </div>
            </div>

            <div className="grid grid-cols-2 justify-center items-center gap-20 pt-5">
              <div className="flex flex-col gap-5">
                <label className="text-[18px] font-semibold">
                  Waterjet Speed (mm/sec)
                </label>
                <Input
                  id="speed"
                  placeholder="0.00"
                  type="number"
                  required
                  className="placeholder:text-lg"
                />
              </div>

              <div className="flex flex-col gap-5">
                <label className="text-[18px] font-semibold">
                  Waterjet Power (kW)
                </label>
                <Input
                  id="speed"
                  placeholder="0.00"
                  type="number"
                  required
                  className="placeholder:text-lg"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 justify-center items-center gap-20 pt-5">
              <div className="flex flex-col gap-5">
                <label className="text-[18px] font-semibold">
                  Waterjet Elec. Rate ($/kWh)
                </label>
                <Input
                  id="speed"
                  placeholder="$ 0.00"
                  type="number"
                  required
                  className="placeholder:text-lg"
                />
              </div>

              <div className="flex flex-col gap-5">
                <label className="text-[18px] font-semibold">
                  Waterjet Machine Rate ($/hr)
                </label>
                <div className="relative w-76">
                  <Input
                    id="speed"
                    type="number"
                    placeholder="$ 0.00"
                    required
                    className="placeholder:text-lg pr-16"
                  />

                  <Button
                    type="button"
                    className="absolute right-1 top-1/2 -translate-y-1/2 h-6 bg-[#cdd9f4] text-[#135BEC] hover:bg-[#cdd9f4]"
                  >
                    Auto
                  </Button>
                </div>
              </div>
            </div>
          </div>

          <div className="pt-10 flex justify-center items-center">
            <Button className="bg-[#135BEC] text-white text-[18px] font-bold p-7 hover:cursor-pointer hover:bg-[#135BEC]">
              Generate Estimates
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default CostEstimation;
