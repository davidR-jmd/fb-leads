import React from 'react';
import { cn } from '../lib/utils';

interface Step {
  number: number;
  label: string;
}

interface StepperProps {
  steps: Step[];
  currentStep: number;
  className?: string;
}

export default function Stepper({ steps, currentStep, className }: StepperProps) {
  return (
    <div className={cn('flex items-center justify-center', className)}>
      {steps.map((step, index) => (
        <React.Fragment key={step.number}>
          <div className="flex items-center">
            <div
              className={cn(
                'flex items-center justify-center w-8 h-8 rounded-full text-sm font-medium',
                currentStep >= step.number
                  ? 'bg-teal-600 text-white'
                  : 'bg-slate-200 text-slate-500'
              )}
            >
              {step.number}
            </div>
            <span
              className={cn(
                'ml-2 text-sm font-medium',
                currentStep >= step.number ? 'text-slate-800' : 'text-slate-400'
              )}
            >
              {step.label}
            </span>
          </div>
          {index < steps.length - 1 && (
            <div
              className={cn(
                'flex-1 h-0.5 mx-4 min-w-[60px]',
                currentStep > step.number ? 'bg-teal-600' : 'bg-slate-200'
              )}
            />
          )}
        </React.Fragment>
      ))}
    </div>
  );
}
