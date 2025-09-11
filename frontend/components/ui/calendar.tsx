"use client";

import * as React from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

export interface CalendarProps {
  mode?: "single" | "multiple" | "range";
  selected?: Date | Date[] | { from?: Date; to?: Date };
  onSelect?: (date: Date | Date[] | { from?: Date; to?: Date } | undefined) => void;
  className?: string;
  showOutsideDays?: boolean;
  disabled?: (date: Date) => boolean;
}

// Simple calendar component as a placeholder until react-day-picker is installed
function Calendar({
  mode = "single",
  selected,
  onSelect,
  className,
  showOutsideDays = true,
  disabled,
}: CalendarProps) {
  const [currentMonth, setCurrentMonth] = React.useState(new Date());
  
  const monthStart = new Date(currentMonth.getFullYear(), currentMonth.getMonth(), 1);
  const monthEnd = new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1, 0);
  const startDate = new Date(monthStart);
  startDate.setDate(startDate.getDate() - startDate.getDay());
  
  const weeks = [];
  const days = [];
  
  for (let i = 0; i < 42; i++) {
    const day = new Date(startDate);
    day.setDate(startDate.getDate() + i);
    days.push(day);
    
    if (days.length === 7) {
      weeks.push([...days]);
      days.length = 0;
    }
  }
  
  const isSelected = (date: Date) => {
    if (!selected) return false;
    if (mode === "single" && selected instanceof Date) {
      return date.toDateString() === selected.toDateString();
    }
    return false;
  };
  
  const isToday = (date: Date) => {
    return date.toDateString() === new Date().toDateString();
  };
  
  const isOutsideMonth = (date: Date) => {
    return date.getMonth() !== currentMonth.getMonth();
  };
  
  const handleDateClick = (date: Date) => {
    if (disabled?.(date)) return;
    if (isOutsideMonth(date) && !showOutsideDays) return;
    
    if (mode === "single") {
      onSelect?.(date);
    }
  };
  
  const goToPreviousMonth = () => {
    setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() - 1));
  };
  
  const goToNextMonth = () => {
    setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1));
  };
  
  return (
    <div className={cn("p-3", className)}>
      <div className="flex flex-col space-y-4">
        <div className="flex justify-center pt-1 relative items-center">
          <Button
            variant="outline"
            className="h-7 w-7 bg-transparent p-0 opacity-50 hover:opacity-100 absolute left-1"
            onClick={goToPreviousMonth}
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <div className="text-sm font-medium">
            {currentMonth.toLocaleDateString('en-US', { month: 'long', year: 'numeric' })}
          </div>
          <Button
            variant="outline"
            className="h-7 w-7 bg-transparent p-0 opacity-50 hover:opacity-100 absolute right-1"
            onClick={goToNextMonth}
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
        <table className="w-full border-collapse space-y-1">
          <thead>
            <tr className="flex">
              {['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa'].map((day) => (
                <th
                  key={day}
                  className="text-muted-foreground rounded-md w-9 font-normal text-[0.8rem]"
                >
                  {day}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {weeks.map((week, weekIdx) => (
              <tr key={weekIdx} className="flex w-full mt-2">
                {week.map((day, dayIdx) => {
                  const isDisabled = disabled?.(day) || false;
                  const isOutside = isOutsideMonth(day);
                  const selected = isSelected(day);
                  const today = isToday(day);
                  
                  return (
                    <td
                      key={dayIdx}
                      className="h-9 w-9 text-center text-sm p-0 relative"
                    >
                      <Button
                        variant="ghost"
                        className={cn(
                          "h-9 w-9 p-0 font-normal",
                          selected && "bg-primary text-primary-foreground hover:bg-primary hover:text-primary-foreground",
                          today && !selected && "bg-accent text-accent-foreground",
                          isOutside && "text-muted-foreground opacity-50",
                          isDisabled && "text-muted-foreground opacity-50 cursor-not-allowed",
                          !isOutside && !showOutsideDays && "invisible"
                        )}
                        onClick={() => handleDateClick(day)}
                        disabled={isDisabled || (isOutside && !showOutsideDays)}
                      >
                        {day.getDate()}
                      </Button>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

Calendar.displayName = "Calendar";

export { Calendar };