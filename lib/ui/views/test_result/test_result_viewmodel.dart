import 'package:stacked/stacked.dart';
import 'package:vital_step/Model/test.dart';
import 'package:vital_step/app/app.locator.dart';
import 'package:vital_step/services/api_calls_service.dart';

class TestResultViewModel extends BaseViewModel {
  late Future<Test?> testFuture;
  Test? test;
  final _apiCallsService = locator<ApiCallsService>();
  Future<Test?> init() async {
    test = await _apiCallsService.getLastTest();
    return test;
  }

  String getDate(DateTime createdAt) {
    return "${createdAt.day}/${createdAt.month}/${createdAt.year}";
  }

  String getTime(DateTime createdAt) {
    return "${createdAt.hour}:${createdAt.minute}";
  }
}
