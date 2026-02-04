import 'package:stacked/stacked.dart';
import 'package:url_launcher/url_launcher.dart';

class KillAppViewModel extends BaseViewModel {
  void contactDeveloper() {
    final _url = Uri.parse('https://wa.me/916396116270');
    launchUrl(_url);
  }
}
