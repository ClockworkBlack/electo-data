package org.electo.app;

import android.content.res.Configuration;
import android.os.Bundle;
import android.view.ViewGroup;
import android.webkit.RenderProcessGoneDetail;
import android.webkit.WebView;
import androidx.activity.OnBackPressedCallback;
import androidx.core.view.WindowCompat;
import androidx.core.view.WindowInsetsControllerCompat;
import com.getcapacitor.BridgeActivity;
import com.getcapacitor.WebViewListener;

/**
 * Electo's activity: Capacitor's own, plus the page's theme from the first moment (no title bar of Android's own), a
 * guard that restarts the page instead of letting the app close when Android kills it, a Back button that closes the
 * page's popups first, and system bars in the page's own colours.
 * Copied over the generated MainActivity after `npx cap add android` (app/android.sh in electo-data,
 * tools/app_android.sh in Electo: the two repositories keep the same file).
 */
public class MainActivity extends BridgeActivity {
    private long lastRecovery = 0;
    private int recoveries = 0;

    @Override
    public void onCreate(Bundle savedInstanceState) {
        // 1. The page's own theme (no title bar) before anything else. Capacitor sets it too, but only after the
        //    activity's own start. On Android 14 that was too late while this file still set the service worker
        //    client at this point (which starts the WebView ahead of the window): the window came up with the opening
        //    screen's theme, "Electo" in a title bar over the page and the opening picture squeezed into it. Two test
        //    builds in the Android 14 emulator (Nov. 12, 2026) each ended it: this line first, and the service worker
        //    lines moved behind the start. Both hold here: this line, and no service worker lines at all (below).
        //    Android 15 never showed the bar.
        setTheme(R.style.AppTheme_NoActionBar);
        // A service worker left by an older build asks for the app's files from its own thread, which the page's
        // local server would not see. Capacitor routes those requests to that server itself when it loads the page
        // (android.resolveServiceWorkerRequests, on unless capacitor.config.json turns it off), replacing whatever
        // client was set before, so the lines that used to do the same here did nothing but start the WebView early.
        super.onCreate(savedInstanceState);
        bars();
        if (bridge == null) return; // no WebView on this device: Capacitor shows its own message
        // 2. If the page's process is killed (most often for memory while the offline AI loads), Android closes the
        //    whole app unless someone handles it. Start the page again instead; it finds the note it left before the
        //    load and uses a lighter setting next time. A page that keeps dying closes rather than looping.
        bridge.addWebViewListener(new WebViewListener() {
            @Override
            public boolean onRenderProcessGone(WebView view, RenderProcessGoneDetail detail) {
                try {
                    if (view.getParent() instanceof ViewGroup) ((ViewGroup) view.getParent()).removeView(view);
                    view.destroy();
                } catch (Exception ignored) {
                    // the WebView is already gone
                }
                recover();
                return true;
            }
        });
        // 3. Back: the page closes its top popup or steps back out of a profile (window.electoBack); when nothing is
        //    open, the app goes to the background instead of closing, so it opens again at once, as it was.
        getOnBackPressedDispatcher().addCallback(this, new OnBackPressedCallback(true) {
            @Override
            public void handleOnBackPressed() {
                final WebView wv = bridge != null ? bridge.getWebView() : null;
                if (wv == null) {
                    moveTaskToBack(true);
                    return;
                }
                wv.evaluateJavascript("(function(){try{return !!(window.electoBack&&window.electoBack())}catch(e){return false}})()", value -> {
                    if ("true".equals(value)) return;
                    if (wv.canGoBack()) wv.goBack();
                    else moveTaskToBack(true);
                });
            }
        });
    }

    @Override
    public void onConfigurationChanged(Configuration newConfig) {
        super.onConfigurationChanged(newConfig);
        bars(); // the phone switched between light and dark
    }

    // 4. The status bar and the navigation bar take the page's background (light, or dark when the phone is set to
    //    dark, as the page itself does), with the clock and icons dark on light and light on dark. Android 15 and
    //    later draw the page behind both bars and ignore the colours; the icons' setting is what counts there
    //    (without it they are white on the page's light background).
    @SuppressWarnings("deprecation")
    private void bars() {
        try {
            boolean night = (getResources().getConfiguration().uiMode & Configuration.UI_MODE_NIGHT_MASK) == Configuration.UI_MODE_NIGHT_YES;
            int bg = night ? 0xFF121619 : 0xFFF3F5F7;
            getWindow().setStatusBarColor(bg);
            getWindow().setNavigationBarColor(bg);
            WindowInsetsControllerCompat c = WindowCompat.getInsetsController(getWindow(), getWindow().getDecorView());
            c.setAppearanceLightStatusBars(!night);
            c.setAppearanceLightNavigationBars(!night);
        } catch (Exception ignored) {
            // an Android without these settings: the bars keep their own colours
        }
    }

    private void recover() {
        long now = System.currentTimeMillis();
        recoveries = now - lastRecovery < 60000 ? recoveries + 1 : 1;
        lastRecovery = now;
        if (recoveries > 3) {
            finish();
            return;
        }
        runOnUiThread(this::recreate);
    }
}
