import React from 'react';
import { Spinner } from './ui/spinner';
import { t } from '../i18n';
import { useBrandingLogo, useBrandingAppName } from '../lib/branding-api';

const DEFAULT_LOGO = '/assets/ury/pos/ury_pos.png';
const DEFAULT_APP_NAME = 'URY POS';

const InitialLoader: React.FC = () => {
  const logoUrl = useBrandingLogo();
  const appName = useBrandingAppName();

  return (
    <div className="fixed inset-0 bg-white flex items-center justify-center">
      <div className="text-center">
        <img src={logoUrl || DEFAULT_LOGO} alt="Logo" className="h-16 w-auto mx-auto mb-6" />
        <Spinner className="w-12 h-12" />
        <p className="mt-4 text-lg font-medium text-gray-900">
          {t('common.loading_ury_pos', { appName: appName || DEFAULT_APP_NAME })}
        </p>
        <p className="mt-2 text-sm text-gray-500">{t('common.please_wait_setup')}</p>
      </div>
    </div>
  );
};

export default InitialLoader;
