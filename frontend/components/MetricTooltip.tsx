"use client";
import { useState, useRef, useId } from "react";

export default function MetricTooltip({ content }: { content: string }) {
  const [visible, setVisible] = useState(false);
  const [above, setAbove] = useState(true);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const tooltipId = useId();

  function show() {
    if (triggerRef.current) {
      setAbove(triggerRef.current.getBoundingClientRect().top > 120);
    }
    setVisible(true);
  }

  return (
    <span
      className="relative inline-flex items-center"
      onMouseEnter={show}
      onMouseLeave={() => setVisible(false)}
    >
      <button
        ref={triggerRef}
        type="button"
        aria-describedby={visible ? tooltipId : undefined}
        onFocus={show}
        onBlur={() => setVisible(false)}
        onClick={() => (visible ? setVisible(false) : show())}
        className="ml-1.5 text-gray-500 hover:text-gray-300 transition-colors focus:outline-none focus-visible:ring-1 focus-visible:ring-primary rounded-full"
        aria-label="Accuracy information"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 20 20"
          fill="currentColor"
          className="w-3.5 h-3.5"
        >
          <path
            fillRule="evenodd"
            d="M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0Zm-7-4a1 1 0 1 1-2 0 1 1 0 0 1 2 0ZM9 9a.75.75 0 0 0 0 1.5h.253a.25.25 0 0 1 .244.304l-.459 2.066A1.75 1.75 0 0 0 10.747 15H11a.75.75 0 0 0 0-1.5h-.253a.25.25 0 0 1-.244-.304l.459-2.066A1.75 1.75 0 0 0 9.253 9H9Z"
            clipRule="evenodd"
          />
        </svg>
      </button>

      {visible && (
        <div
          id={tooltipId}
          role="tooltip"
          className={`absolute z-50 w-[200px] text-xs text-gray-200 bg-gray-900 border border-white/15 rounded-lg px-3 py-2.5 leading-relaxed shadow-xl pointer-events-none left-1/2 -translate-x-1/2 ${
            above ? "bottom-full mb-2" : "top-full mt-2"
          }`}
        >
          {content}
          <span
            className={`absolute left-1/2 -translate-x-1/2 w-0 h-0 border-x-[5px] border-x-transparent ${
              above
                ? "top-full border-t-[6px] border-t-gray-900"
                : "bottom-full border-b-[6px] border-b-gray-900"
            }`}
          />
        </div>
      )}
    </span>
  );
}
