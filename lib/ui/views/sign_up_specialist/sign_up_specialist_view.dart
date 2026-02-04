import 'package:flutter/material.dart';
import 'package:stacked/stacked.dart';
import 'package:stacked/stacked_annotations.dart';
import 'package:vital_step/Model/spcialist_profile.dart';
import 'package:vital_step/ui/common/FormValidators.dart';
import 'package:vital_step/ui/common/app_colors.dart';
import 'package:vital_step/ui/common/app_strings.dart';
import 'package:vital_step/ui/common/ui_helpers.dart';
import 'package:vital_step/ui/views/sign_up/sign_up_view.dart';
import 'package:vital_step/ui/views/sign_up_specialist/sign_up_specialist_view.form.dart';

import 'sign_up_specialist_viewmodel.dart';

@FormView(fields: [
  FormTextField(name: 'name', validator: FormValidators.nameValidator),
  FormTextField(
      name: 'mobileNumber', validator: FormValidators.mobileNumberValidator),
  FormTextField(name: 'email', validator: FormValidators.emailValidator),
  FormTextField(name: 'password', validator: FormValidators.passwordValidator),
  FormDateField(name: 'dob'),
  FormTextField(name: 'city'),
  FormTextField(name: 'country'),
  FormTextField(name: 'pincode'),
  FormDropdownField(
      items: countryCodeDropDownItems, name: "countryCodeDropDown")
])
class SignUpSpecialistView extends StackedView<SignUpSpecialistViewModel>
    with $SignUpSpecialistView {
  SignUpSpecialistView({Key? key, this.profile}) : super(key: key);
  final ProfileSpecialist? profile;
  final inputStyle = InputDecoration(
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(10.0), // Add border radius
        borderSide: BorderSide.none, // Remove the default border
      ),
      fillColor: Colors.grey[200],
      filled: true);

  @override
  Widget builder(
    BuildContext context,
    SignUpSpecialistViewModel viewModel,
    Widget? child,
  ) {
    final bool update = profile != null;
    return Scaffold(
      backgroundColor: Colors.white,
      body: Container(
        padding: const EdgeInsets.only(left: 25.0, right: 25.0),
        child: Form(
            key: viewModel.formKey,
            child: ListView(
              children: [
                SignUpHeader(update: update),
                TextFormField(
                  controller: nameController,
                  decoration: inputStyle.copyWith(labelText: 'Name[Required]'),
                  validator: FormValidators.nameValidator,
                ),
                verticalSpaceSmall,

                const Text('CountryCode [Required] '),
                DropdownButton<String>(
                  key: const ValueKey('countryCodesDropDownField'),
                  value: viewModel.countryCodeDropDownValue,
                  onChanged: (value) {
                    viewModel.setCountryCodeDropDown(value!);
                  },
                  isExpanded: true,
                  items: CountryCodeDropDownValueToTitleMap.keys
                      .map(
                        (value) => DropdownMenuItem<String>(
                          key: ValueKey('$value key'),
                          value: value,
                          child:
                              Text(CountryCodeDropDownValueToTitleMap[value]!),
                        ),
                      )
                      .toList(),
                ),

                verticalSpaceSmall,
                TextFormField(
                  controller: mobileNumberController,
                  decoration: inputStyle.copyWith(
                      labelText: 'Mobile Number [Required]'),
                  keyboardType: TextInputType.phone,
                  validator: FormValidators.mobileNumberValidator,
                  enabled: profile == null ? true : false,
                ),
                verticalSpaceSmall,
                TextFormField(
                  controller: emailController,
                  decoration:
                      inputStyle.copyWith(labelText: 'Email [Required]'),
                  keyboardType: TextInputType.emailAddress,
                  validator: FormValidators.emailValidator,
                  enabled: profile == null ? true : false,
                ),
                verticalSpaceSmall,
                update
                    ? const SizedBox()
                    : TextFormField(
                        controller: passwordController,
                        decoration: InputDecoration(
                            labelText: 'Password [Required]',
                            border: InputBorder.none,
                            fillColor: Colors.grey[200],
                            filled: true,
                            suffixIcon: IconButton(
                              icon: Icon(viewModel.passwordVisible
                                  ? Icons.visibility
                                  : Icons.visibility_off),
                              onPressed: () {
                                viewModel.passwordVisible =
                                    !viewModel.passwordVisible;
                                viewModel.rebuildUi();
                              },
                            )),
                        obscureText: viewModel.passwordVisible,
                        validator: FormValidators.passwordValidator,
                      ),
                verticalSpaceSmall,
                TextFormField(
                  controller: viewModel.viewDobController,
                  decoration:
                      inputStyle.copyWith(labelText: 'Date of Birth[Required]'),
                  readOnly: true,
                  onTap: () async {
                    viewModel.setDOB(context);
                  },
                ),
                verticalSpaceSmall,
                // city
                TextFormField(
                  controller: cityController,
                  decoration: inputStyle.copyWith(labelText: 'City'),
                ),
                verticalSpaceSmall,
                // pincode
                TextFormField(
                  controller: pincodeController,
                  decoration: inputStyle.copyWith(labelText: 'pincode'),
                  keyboardType: TextInputType.number,
                ),
                verticalSpaceSmall,
                TextFormField(
                  controller: countryController,
                  decoration: inputStyle.copyWith(labelText: 'Country'),
                ),
                verticalSpaceSmall,

                InkWell(
                  onTap: () async {
                    if (viewModel.isBusy) {
                      return;
                    }
                    if (profile == null) {
                      await viewModel.saveData(update: false);
                    } else if (profile != null) {
                      await viewModel.saveData(update: true);
                    }
                  },
                  child: Container(
                    height: 55,
                    margin: const EdgeInsets.only(top: 30),
                    width: double.infinity,
                    decoration: BoxDecoration(
                      color: kcPrimaryColor,
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: viewModel.isBusy
                        ? const Center(
                            child: CircularProgressIndicator(
                              color: Colors.white,
                            ),
                          )
                        : Center(
                            child: Text(
                              profile == null ? "Sign Up" : 'Update',
                              style: const TextStyle(
                                fontSize: 16,
                                color: Colors.white,
                              ),
                            ),
                          ),
                  ),
                ),
                verticalSpaceSmall,
                profile == null ? const SignUpBottom() : const SizedBox()
              ],
            )),
      ),
    );
  }

  @override
  SignUpSpecialistViewModel viewModelBuilder(
    BuildContext context,
  ) =>
      SignUpSpecialistViewModel();
  @override
  void onViewModelReady(SignUpSpecialistViewModel viewModel) {
    syncFormWithViewModel(viewModel);
    if (profile != null) {
      viewModel.setProfile(profile!);
    }
  }
}
