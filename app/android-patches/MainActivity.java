package org.electo.app;

import android.content.res.Configuration;
import android.os.Build;
import android.os.Bundle;
import android.view.ViewGroup;
import android.webkit.RenderProcessGoneDetail;
import android.webkit.ServiceWorkerClient;
import android.webkit.ServiceWorkerController;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebView;
import androidx.activity.OnBackPressedCallback;
import androidx.core.view.WindowCompat;
import androidx.core.view.WindowInsetsControllerCompat;
import com.getcapacitor.BridgeActivity;
import com.getcapacitor.WebViewListener;

/**
 * Electo's activity: Capacitor's own, plus guards that keep the app from opening blank or closing outright, a Back
 * button that closes the page's popups first, and system bars in the page's own colours.
 * Copied over the generated MainActivity after `npx cap add android` (app/android.sh in electo-data,
 * tools/app_android.sh in Electo: the two repositories keep the same file).
 */
public class MainActivity extends BridgeActivity {
    private long lastRecovery = 0;
    private int recoveries = 0;

    @Override
    public void onCreate(Bundle savedInstanceState) {
        // 0. The page's own theme (no title bar) before anything builds the window. Capacitor sets it too, but only
        //    after the activity's own start; on Android 14 the window had been built by then, with the opening
        //    screen's theme, which has a title bar there: "Electo" in a bar over the page, the opening picture
        //    squeezed into it (the Android 14 emulator, Nov. 12, 2026; Android 15 did not show it).
        // 1. A service worker left by an older build (or a website copy) asks for the app's files from its own thread,
        //    which Capacitor's local server never sees: the request fails and the page can open as a white screen.
        //    Route those requests to the same local server as every other request. (The page itself no longer
        //    registers a service worker inside the app, and removes any it finds.)
        super.onCreate(savedInstanceState);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
            try {
                ServiceWorkerController.getInstance().setServiceWorkerClient(new ServiceWorkerClient() {
                    @Override
                    public WebResourceResponse shouldInterceptRequest(WebResourceRequest request) {
                        return bridge != null ? bridge.getLocalServer().shouldInterceptRequest(request) : null;
                    }
                });
            } catch (Exception ignored) {
                // no service worker support in this WebView: nothing to route
            }
        }
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
