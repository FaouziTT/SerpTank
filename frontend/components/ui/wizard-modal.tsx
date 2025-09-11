'use client';

import * as React from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { ChevronLeft, ChevronRight } from 'lucide-react';

export interface WizardStep {
  id: string;
  title: string;
  description?: string;
  content: React.ReactNode;
  isValid?: boolean;
  onValidate?: () => Promise<boolean> | boolean;
}

export interface WizardModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description?: string;
  steps: WizardStep[];
  onComplete: () => void | Promise<void>;
  completionLabel?: string;
  className?: string;
  showProgress?: boolean;
  allowSkip?: boolean;
}

export function WizardModal({
  open,
  onOpenChange,
  title,
  description,
  steps,
  onComplete,
  completionLabel = 'Complete',
  className,
  showProgress = true,
  allowSkip = false,
}: WizardModalProps) {
  const [currentStep, setCurrentStep] = React.useState(0);
  const [isValidating, setIsValidating] = React.useState(false);
  const [isCompleting, setIsCompleting] = React.useState(false);

  const currentStepData = steps[currentStep];
  const isFirstStep = currentStep === 0;
  const isLastStep = currentStep === steps.length - 1;
  const progressPercentage = ((currentStep + 1) / steps.length) * 100;

  const handleNext = async () => {
    if (currentStepData.onValidate) {
      setIsValidating(true);
      try {
        const isValid = await currentStepData.onValidate();
        if (!isValid) {
          setIsValidating(false);
          return;
        }
      } catch (error) {
        setIsValidating(false);
        return;
      }
      setIsValidating(false);
    }

    if (isLastStep) {
      handleComplete();
    } else {
      setCurrentStep(currentStep + 1);
    }
  };

  const handlePrevious = () => {
    if (!isFirstStep) {
      setCurrentStep(currentStep - 1);
    }
  };

  const handleComplete = async () => {
    setIsCompleting(true);
    try {
      await onComplete();
      onOpenChange(false);
      // Reset to first step for next time
      setCurrentStep(0);
    } catch (error) {
      console.error('Failed to complete wizard:', error);
    } finally {
      setIsCompleting(false);
    }
  };

  const handleSkip = () => {
    if (allowSkip && !isLastStep) {
      setCurrentStep(currentStep + 1);
    }
  };

  // Reset step when modal closes
  React.useEffect(() => {
    if (!open) {
      setCurrentStep(0);
    }
  }, [open]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className={className}>
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          {description && <DialogDescription>{description}</DialogDescription>}
        </DialogHeader>

        <div className="py-4">
          {showProgress && (
            <div className="mb-6">
              <div className="flex justify-between text-sm text-muted-foreground mb-2">
                <span>Step {currentStep + 1} of {steps.length}</span>
                <span>{currentStepData.title}</span>
              </div>
              <Progress value={progressPercentage} className="h-2" />
            </div>
          )}

          <div className="min-h-[200px]">
            <h3 className="text-lg font-semibold mb-2">{currentStepData.title}</h3>
            {currentStepData.description && (
              <p className="text-sm text-muted-foreground mb-4">
                {currentStepData.description}
              </p>
            )}
            {currentStepData.content}
          </div>
        </div>

        <DialogFooter className="flex justify-between">
          <div>
            {!isFirstStep && (
              <Button
                variant="outline"
                onClick={handlePrevious}
                disabled={isValidating || isCompleting}
              >
                <ChevronLeft className="mr-2 h-4 w-4" />
                Previous
              </Button>
            )}
          </div>
          <div className="flex gap-2">
            {allowSkip && !isLastStep && (
              <Button
                variant="ghost"
                onClick={handleSkip}
                disabled={isValidating || isCompleting}
              >
                Skip
              </Button>
            )}
            <Button
              onClick={handleNext}
              disabled={
                isValidating ||
                isCompleting ||
                (currentStepData.isValid !== undefined && !currentStepData.isValid)
              }
            >
              {isValidating || isCompleting ? (
                <>Loading...</>
              ) : isLastStep ? (
                completionLabel
              ) : (
                <>
                  Next
                  <ChevronRight className="ml-2 h-4 w-4" />
                </>
              )}
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}