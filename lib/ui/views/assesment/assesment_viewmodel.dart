import 'dart:ffi';

import 'package:flutter/material.dart';
import 'package:fluttertoast/fluttertoast.dart';
import 'package:stacked/stacked.dart';
import 'package:stacked_services/stacked_services.dart';
import 'package:vital_step/Model/Assessment.dart';
import 'package:vital_step/Model/profile.dart';
import 'package:vital_step/app/app.dialogs.dart';
import 'package:vital_step/app/app.locator.dart';
import 'package:vital_step/app/app.router.dart';
import 'package:vital_step/services/accounts_service.dart';
import 'package:vital_step/services/api_calls_service.dart';
import 'package:vital_step/services/specialist_service.dart';

class AssesmentViewModel extends BaseViewModel {
  final _dialogService = locator<DialogService>();
  final _apiCallsService = locator<ApiCallsService>();
  final _accountsService = locator<AccountsService>();
  final _specialistService = locator<SpecialistService>();
  int? patientUserId;
  bool? isSpecialist;
  late Future<List<Assessment>?> devicesFuture;
  Future<List<Assessment>?> init() async {
    final assessments = await _apiCallsService.getAllUserAssessments(
        patientUserId: patientUserId);
    return assessments;
  }

  Future<void> takeTest(Assessment assessment) async {
    setBusy(true);
    // we need to check the assessment queue.
    final assessmentQueue = await _apiCallsService.getAssessmentQueue(
        assessmentId: assessment.id.toString());
    // if the queue is empty, then give a popup and create a test
    if (assessmentQueue.isEmpty) {
      // show a popup that the queue is empty.
      await _dialogService.showCustomDialog(
          variant: DialogType.createTest, data: assessment.toJson());
      setBusy(false);

      devicesFuture = init();
      rebuildUi();
      return;
    } else {
      // if the queue is not empty then we take him to the result page.
      await NavigationService()
          .navigateToTestTakingView(assessment: assessment);
      devicesFuture = init();
      rebuildUi();
      return;
    }
  }

  Future<Profile> getPatientProfile({int? patientUserId}) async {
    final profile =
        await _accountsService.getAccountDetails(patientUserId: patientUserId);
    return profile;
  }

  final deletingUser = "deleting User";
  void deleteUser(int? id) async {
    setBusyForObject(deletingUser, true);
    final dialogService = locator<DialogService>();
    final response = await dialogService.showConfirmationDialog(
      title: "Do you want to delete this user?",
      description: "This action cannot be undone",
    );
    if (response != null && response.confirmed == true) {
      await _specialistService.deleteAccountAccess(id: id);
    } else {
      Fluttertoast.showToast(msg: "User not deleted");
    }
    setBusyForObject(deletingUser, false);
  }

  void deleteAssessment({required String assessmentId}) async {
    final dialogService = locator<DialogService>();
    final response = await dialogService.showConfirmationDialog(
      title: "Do you want to delete this assessment?",
      description: "This action cannot be undone",
    );
    if (response != null && response.confirmed == true) {
      await _specialistService.deleteAssessment(assessmentId: assessmentId);
      devicesFuture = init();
    } else {
      Fluttertoast.showToast(msg: "Assessment not deleted");
    }
    rebuildUi();
  }
}
