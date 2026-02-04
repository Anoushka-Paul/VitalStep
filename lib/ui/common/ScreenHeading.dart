import 'package:flutter/material.dart';

class ScreenHeading extends StatefulWidget {
  String heading = "";
  bool showBackButton;
  Function? callbackFunction;
  Color? color;
  ScreenHeading(
      {required this.heading,
      required this.showBackButton,
      this.color,
      this.callbackFunction});

  @override
  State<ScreenHeading> createState() => _ScreenHeadingState();
}

class _ScreenHeadingState extends State<ScreenHeading> {
  @override
  Widget build(BuildContext context) {
    return Container(
      padding: EdgeInsets.only(
          left: 20,
          right: 20,
          top: MediaQuery.of(context).padding.top + 20,
          bottom: 20),
      child: Stack(
        children: [
          Container(
            height: 30,
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Container(
                    child: Text(
                  widget.heading,
                  style: TextStyle(
                    fontSize: 20,
                    color: widget.color != null ? Colors.white : widget.color,
                    fontWeight: FontWeight.bold,
                  ),
                )),
              ],
            ),
          ),
          Container(
            height: 30,
            child: Row(
              mainAxisAlignment: MainAxisAlignment.start,
              crossAxisAlignment: CrossAxisAlignment.center,
              children: [
                (widget.showBackButton)
                    ? GestureDetector(
                        onTap: () {
                          if (widget.callbackFunction != null) {
                            widget.callbackFunction!();
                          }
                        },
                        child: Icon(
                          Icons.arrow_back_ios,
                          size: 20,
                        ),
                      )
                    : Container()
              ],
            ),
          ),
        ],
      ),
    );
  }
}
