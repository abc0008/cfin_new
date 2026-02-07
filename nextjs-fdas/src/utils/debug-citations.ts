// Debug utility to check citation state
export function debugCitations() {
  // Check if we have messages with citations
  const messagesElement = document.querySelector('[class*="message-content"]');
  console.log('Messages found:', !!messagesElement);
  
  // Check for citation markers in text
  const textContent = document.body.innerText;
  const citationMarkers = textContent.match(/\[\d+\]/g);
  console.log('Citation markers in text:', citationMarkers);
  
  // Check for citation buttons
  const citationButtons = document.querySelectorAll('button[class*="citation"]');
  console.log('Citation buttons found:', citationButtons.length);
  
  // Check for MessageRenderer components
  const messageRenderers = document.querySelectorAll('[class*="message-content"]');
  console.log('MessageRenderer elements:', messageRenderers.length);
  
  // Log React component props if available
  if ((window as any).React && (window as any).React.__SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED) {
    console.log('React internals available for debugging');
  }
  
  return {
    hasMessages: !!messagesElement,
    citationMarkers,
    citationButtonCount: citationButtons.length,
    messageRendererCount: messageRenderers.length
  };
}

// Auto-run on page load for debugging
if (typeof window !== 'undefined') {
  window.addEventListener('load', () => {
    setTimeout(() => {
      console.log('Citation Debug:', debugCitations());
    }, 2000);
  });
}