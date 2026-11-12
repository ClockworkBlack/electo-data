package org.electo.app;

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
import com.getcapacitor.BridgeActivity;
import com.getcapacitor.WebViewListener;

/**
 * Electo's activity: Capacitor's own, plus guards that keep the app from opening blank or closing outright, and a
 * Back button that closes the page's popups first.
 * Copied over the generated MainActivity by app/android.sh after `npx cap add android`.
 */
public class MainActivity extends BridgeActivity {
    private long lastRecovery = 0;
    private int recoveries = 0;

    @Override
    public void onCreate(Bundle savedInstanceState) {
        // 1. A service worker left by an older build (or a website copy) asks for the app's files from its own thread,
        //    which Capacitor's local server never sees: the request fails and the page can open as a white screen.
        //    Route those requests to the same local server as every other request. (The page itself no longer
        //    registers a service worker inside the app, and removes any it finds.)
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
        super.onCreate(savedInstanceState);
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
