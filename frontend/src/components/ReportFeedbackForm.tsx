"use client";

import { FormEvent, useId, useState } from "react";

import { submitModelFeedback } from "@/lib/api";
import type { ModelFeedbackCategory } from "@/lib/types";

type ReportFeedbackFormProps = {
  reportId: string;
};

const categories: Array<{ value: ModelFeedbackCategory; label: string }> = [
  { value: "helpful", label: "Helpful" },
  { value: "incorrect", label: "Incorrect" },
  { value: "missing_source", label: "Missing source" },
  { value: "bad_citation", label: "Bad citation" },
  { value: "unclear", label: "Unclear" },
  { value: "entity_error", label: "Entity error" },
  { value: "unsafe", label: "Unsafe" }
];

export function ReportFeedbackForm({ reportId }: ReportFeedbackFormProps) {
  const commentId = useId();
  const [category, setCategory] = useState<ModelFeedbackCategory>("helpful");
  const [comment, setComment] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSubmitting(true);
    setError(null);
    setMessage(null);
    try {
      await submitModelFeedback(reportId, {
        category,
        ...(comment.trim() ? { comment: comment.trim() } : {})
      });
      setComment("");
      setMessage("Feedback submitted for review.");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Feedback could not be submitted.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <section className="panel feedback-form" aria-labelledby="report-feedback-heading">
      <h2 id="report-feedback-heading">Report feedback</h2>
      <form onSubmit={(event) => void submit(event)}>
        <label>
          Category
          <select value={category} onChange={(event) => setCategory(event.target.value as ModelFeedbackCategory)}>
            {categories.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
          </select>
        </label>
        <label htmlFor={commentId}>
          Comment <span className="field-help">Optional</span>
          <textarea
            id={commentId}
            value={comment}
            maxLength={1000}
            rows={4}
            onChange={(event) => setComment(event.target.value)}
          />
          <span className="field-help">{comment.length}/1000 characters</span>
        </label>
        {error ? <p className="error" role="alert">{error}</p> : null}
        <p aria-live="polite" className="field-help">{message}</p>
        <button className="secondary-action" disabled={isSubmitting} type="submit">
          {isSubmitting ? "Submitting..." : "Submit feedback"}
        </button>
      </form>
    </section>
  );
}
