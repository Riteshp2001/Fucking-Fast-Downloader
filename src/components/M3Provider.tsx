'use client';
import { useEffect, type ReactNode } from 'react';

export default function M3Provider({ children }: { children: ReactNode }) {
  useEffect(() => {
    import('@material/web/button/filled-button.js');
    import('@material/web/button/outlined-button.js');
    import('@material/web/button/text-button.js');
    import('@material/web/iconbutton/icon-button.js');
    import('@material/web/checkbox/checkbox.js');
    import('@material/web/progress/linear-progress.js');
    import('@material/web/dialog/dialog.js');
  }, []);

  return <>{children}</>;
}
