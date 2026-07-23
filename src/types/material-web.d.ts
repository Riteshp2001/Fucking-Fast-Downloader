import 'react';

declare global {
  namespace JSX {
    interface IntrinsicElements {
      'md-filled-button': React.DetailedHTMLProps<React.HTMLAttributes<HTMLElement> & { disabled?: boolean }, HTMLElement>;
      'md-outlined-button': React.DetailedHTMLProps<React.HTMLAttributes<HTMLElement> & { disabled?: boolean }, HTMLElement>;
      'md-icon-button': React.DetailedHTMLProps<React.HTMLAttributes<HTMLElement> & { disabled?: boolean; title?: string }, HTMLElement>;
      'md-switch': React.DetailedHTMLProps<React.HTMLAttributes<HTMLElement> & { selected?: boolean; disabled?: boolean }, HTMLElement>;
    }
  }
}
